import discord
import json
import os
import re
import traceback
from datetime import datetime, timedelta, timezone
from discord.ext import commands
from discord import app_commands

from cogs.moderation import (
    has_mod_permission,
    add_sanction,
    send_mod_log,
    send_dm,
    build_log_embed,
)

# ─────────────────────────────────────────
#  DA AERON
# ─────────────────────────────────────────

AERON_LOGO    = "https://media.discordapp.net/attachments/1081628825798058079/1517942955254747227/logo.png?ex=6a381e0a&is=6a36cc8a&hm=355f5b01ca46bb58ffce952cfa88e82fdcc39d9205525331a623c3a173958aca&=&format=webp&quality=lossless"
COLOR_MAIN    = 0x012248
COLOR_SUCCESS = 0x1A6B3A
COLOR_WARN    = 0xB8860B
COLOR_DANGER  = 0x8B1A1A
OWNER_ID      = 219821139910852619
CONFIG_FILE   = "config.json"

DEFAULT_AUTOMOD = {
    "antispam": {
        "enabled": False,
        "max_messages": 5,
        "interval_seconds": 5,
        "timeout_seconds": 60,
    },
    "anti_invite": {
        "enabled": False,
    },
    "anti_alt": {
        "enabled": False,
        "min_account_age_days": 7,
        "action": "alert",  # "alert" ou "kick"
    },
}

INVITE_REGEX = re.compile(
    r"(?:discord\.gg/|discord(?:app)?\.com/invite/)([a-zA-Z0-9-]+)",
    re.IGNORECASE,
)

# ─────────────────────────────────────────
#  UTILS — CONFIG
# ─────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_automod_config():
    config = load_config()
    automod = config.get("automod", {})
    # On complète avec les valeurs par défaut si des clés manquent
    for key, defaults in DEFAULT_AUTOMOD.items():
        automod.setdefault(key, {})
        for sub_key, value in defaults.items():
            automod[key].setdefault(sub_key, value)
    return automod

def save_automod_config(automod: dict):
    config = load_config()
    config["automod"] = automod
    save_config(config)

# ─────────────────────────────────────────
#  EMBED — RÉSUMÉ ANTI-ABUS
# ─────────────────────────────────────────

def build_automod_embed(automod: dict) -> discord.Embed:
    antispam = automod["antispam"]
    invite   = automod["anti_invite"]
    alt      = automod["anti_alt"]

    def state(enabled: bool) -> str:
        return "✅ Activé" if enabled else "❌ Désactivé"

    embed = discord.Embed(
        title="◈  SETTINGS — ANTI-ABUS  ◈",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚨 **Antispam** — {state(antispam['enabled'])}\n"
            f"　　`{antispam['max_messages']}` messages / `{antispam['interval_seconds']}`s "
            f"→ mute `{antispam['timeout_seconds']}`s\n\n"
            f"🚫 **Anti-invitation** — {state(invite['enabled'])}\n"
            f"　　Supprime les liens d'invitation vers d'autres serveurs\n\n"
            f"🕵️ **Anti multi-compte** — {state(alt['enabled'])}\n"
            f"　　Seuil : `{alt['min_account_age_days']}` jour(s)  •  "
            f"Action : `{'Kick auto' if alt['action'] == 'kick' else 'Alerte staff'}`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=COLOR_MAIN,
    )
    embed.set_thumbnail(url=AERON_LOGO)
    embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
    return embed

# ─────────────────────────────────────────
#  MODALS — SEUILS
# ─────────────────────────────────────────

class AntispamThresholdsModal(discord.ui.Modal, title="Seuils de l'antispam"):
    def __init__(self, cfg: dict):
        super().__init__()
        self.max_messages = discord.ui.TextInput(
            label="Messages max sur l'intervalle",
            default=str(cfg["max_messages"]),
            max_length=3,
        )
        self.interval_seconds = discord.ui.TextInput(
            label="Intervalle (secondes)",
            default=str(cfg["interval_seconds"]),
            max_length=3,
        )
        self.timeout_seconds = discord.ui.TextInput(
            label="Durée du mute (secondes)",
            default=str(cfg["timeout_seconds"]),
            max_length=5,
        )
        self.add_item(self.max_messages)
        self.add_item(self.interval_seconds)
        self.add_item(self.timeout_seconds)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            max_messages     = int(self.max_messages.value)
            interval_seconds = int(self.interval_seconds.value)
            timeout_seconds  = int(self.timeout_seconds.value)
        except ValueError:
            await interaction.response.send_message("❌ Les 3 valeurs doivent être des nombres.", ephemeral=True)
            return

        if max_messages < 1 or interval_seconds < 1 or timeout_seconds < 1:
            await interaction.response.send_message("❌ Les valeurs doivent être supérieures à 0.", ephemeral=True)
            return

        automod = get_automod_config()
        automod["antispam"]["max_messages"]     = max_messages
        automod["antispam"]["interval_seconds"] = interval_seconds
        automod["antispam"]["timeout_seconds"]  = timeout_seconds
        save_automod_config(automod)

        await interaction.response.edit_message(embed=build_automod_embed(automod), view=AutomodSettingsView())


class AntiAltThresholdModal(discord.ui.Modal, title="Seuil anti multi-compte"):
    def __init__(self, cfg: dict):
        super().__init__()
        self.min_days = discord.ui.TextInput(
            label="Âge minimum du compte (en jours)",
            default=str(cfg["min_account_age_days"]),
            max_length=4,
        )
        self.add_item(self.min_days)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            min_days = int(self.min_days.value)
        except ValueError:
            await interaction.response.send_message("❌ La valeur doit être un nombre.", ephemeral=True)
            return

        if min_days < 0:
            await interaction.response.send_message("❌ La valeur doit être positive.", ephemeral=True)
            return

        automod = get_automod_config()
        automod["anti_alt"]["min_account_age_days"] = min_days
        save_automod_config(automod)

        await interaction.response.edit_message(embed=build_automod_embed(automod), view=AutomodSettingsView())

# ─────────────────────────────────────────
#  VUE : SETTINGS ANTI-ABUS
# ─────────────────────────────────────────

class AutomodSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Antispam On/Off", emoji="🚨", style=discord.ButtonStyle.secondary)
    async def toggle_antispam(self, interaction: discord.Interaction, button: discord.ui.Button):
        automod = get_automod_config()
        automod["antispam"]["enabled"] = not automod["antispam"]["enabled"]
        save_automod_config(automod)
        await interaction.response.edit_message(embed=build_automod_embed(automod), view=self)

    @discord.ui.button(label="Régler l'antispam", emoji="⚙️", style=discord.ButtonStyle.secondary)
    async def configure_antispam(self, interaction: discord.Interaction, button: discord.ui.Button):
        automod = get_automod_config()
        await interaction.response.send_modal(AntispamThresholdsModal(automod["antispam"]))

    @discord.ui.button(label="Anti-invitation On/Off", emoji="🚫", style=discord.ButtonStyle.secondary)
    async def toggle_invite(self, interaction: discord.Interaction, button: discord.ui.Button):
        automod = get_automod_config()
        automod["anti_invite"]["enabled"] = not automod["anti_invite"]["enabled"]
        save_automod_config(automod)
        await interaction.response.edit_message(embed=build_automod_embed(automod), view=self)

    @discord.ui.button(label="Anti multi-compte On/Off", emoji="🕵️", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_alt(self, interaction: discord.Interaction, button: discord.ui.Button):
        automod = get_automod_config()
        automod["anti_alt"]["enabled"] = not automod["anti_alt"]["enabled"]
        save_automod_config(automod)
        await interaction.response.edit_message(embed=build_automod_embed(automod), view=self)

    @discord.ui.button(label="Régler le seuil", emoji="⚙️", style=discord.ButtonStyle.secondary, row=1)
    async def configure_alt(self, interaction: discord.Interaction, button: discord.ui.Button):
        automod = get_automod_config()
        await interaction.response.send_modal(AntiAltThresholdModal(automod["anti_alt"]))

    @discord.ui.button(label="Action : Alerte / Kick", emoji="🔀", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_alt_action(self, interaction: discord.Interaction, button: discord.ui.Button):
        automod = get_automod_config()
        automod["anti_alt"]["action"] = "kick" if automod["anti_alt"]["action"] == "alert" else "alert"
        save_automod_config(automod)
        await interaction.response.edit_message(embed=build_automod_embed(automod), view=self)

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger, row=2)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        from cogs.settings import SettingsMainView, AERON_LOGO as SETTINGS_LOGO, COLOR_MAIN as SETTINGS_COLOR

        embed = discord.Embed(
            title="◈  SETTINGS AERON  ◈",
            description=(
                "Panneau de configuration de la communauté AERON.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Sélectionne un système à configurer."
            ),
            color=SETTINGS_COLOR,
        )
        embed.set_thumbnail(url=SETTINGS_LOGO)
        embed.set_footer(text="AERON • Settings", icon_url=SETTINGS_LOGO)
        await interaction.response.edit_message(embed=embed, view=SettingsMainView())

# ─────────────────────────────────────────
#  COG PRINCIPAL
# ─────────────────────────────────────────

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # user_id -> liste des timestamps de messages récents (antispam)
        self._spam_tracker: dict[int, list[float]] = {}

    # ─────────────────────────────────────
    #  /clear — NETTOYER UN SALON
    # ─────────────────────────────────────

    @app_commands.command(name="clear", description="Supprimer des messages dans ce salon")
    @app_commands.describe(
        nombre="Nombre de messages à supprimer (max 100)",
        membre="Ne supprimer que les messages de ce membre (optionnel)",
    )
    async def clear(
        self,
        interaction: discord.Interaction,
        nombre: app_commands.Range[int, 1, 100],
        membre: discord.Member = None,
    ):
        if not has_mod_permission(interaction, "clear"):
            await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        def check(m: discord.Message) -> bool:
            return membre is None or m.author.id == membre.id

        try:
            deleted = await interaction.channel.purge(limit=nombre, check=check)
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Erreur : `{e}`", ephemeral=True)
            return

        embed = discord.Embed(
            title="◈  SALON NETTOYÉ  ◈",
            description=(
                f"✅ **{len(deleted)}** message{'s' if len(deleted) > 1 else ''} supprimé"
                f"{'s' if len(deleted) > 1 else ''} dans {interaction.channel.mention}."
                + (f"\nFiltré sur {membre.mention}." if membre else "")
            ),
            color=COLOR_SUCCESS,
        )
        embed.set_footer(text="AERON • Modération", icon_url=AERON_LOGO)
        await interaction.followup.send(embed=embed, ephemeral=True)

        await send_mod_log(
            interaction.guild,
            build_log_embed(
                "🧹 Clear",
                interaction.user,
                membre.mention if membre else f"#{interaction.channel.name}",
                f"{len(deleted)} message(s) supprimé(s) dans {interaction.channel.mention}",
                COLOR_SUCCESS,
            ),
        )

    # ─────────────────────────────────────
    #  /compte-info — AIDE MANUELLE ANTI-ALT
    # ─────────────────────────────────────

    @app_commands.command(name="compte-info", description="Voir l'âge et la date d'arrivée d'un membre")
    @app_commands.describe(membre="Le membre à inspecter")
    async def compte_info(self, interaction: discord.Interaction, membre: discord.Member):
        if not has_mod_permission(interaction, "warn"):
            await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
            return

        now = datetime.now(timezone.utc)
        account_age = (now - membre.created_at).days
        join_age = (now - membre.joined_at).days if membre.joined_at else None

        embed = discord.Embed(
            title=f"◈  INFOS COMPTE — {membre.display_name.upper()}  ◈",
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=membre.display_avatar.url)
        embed.add_field(
            name="◈ Compte créé le",
            value=f"<t:{int(membre.created_at.timestamp())}:F>\n({account_age} jour{'s' if account_age > 1 else ''})",
            inline=True,
        )
        if membre.joined_at:
            embed.add_field(
                name="◈ Arrivé sur le serveur le",
                value=f"<t:{int(membre.joined_at.timestamp())}:F>\n({join_age} jour{'s' if join_age and join_age > 1 else ''})",
                inline=True,
            )
        embed.set_footer(text="AERON • Anti multi-compte", icon_url=AERON_LOGO)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ─────────────────────────────────────
    #  ANTISPAM + ANTI-INVITE
    # ─────────────────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        automod = get_automod_config()

        if automod["antispam"]["enabled"]:
            await self._handle_antispam(message, automod["antispam"])

        if automod["anti_invite"]["enabled"]:
            await self._handle_anti_invite(message, automod["anti_invite"])

    def _is_exempt(self, member: discord.Member) -> bool:
        if member.id == OWNER_ID:
            return True
        perms = member.guild_permissions
        return perms.administrator or perms.manage_messages or perms.manage_guild

    async def _handle_antispam(self, message: discord.Message, cfg: dict):
        member = message.author
        if self._is_exempt(member):
            return

        now = datetime.now().timestamp()
        max_messages    = cfg.get("max_messages", 5)
        interval        = cfg.get("interval_seconds", 5)
        timeout_seconds = cfg.get("timeout_seconds", 60)

        timestamps = self._spam_tracker.setdefault(member.id, [])
        timestamps.append(now)
        timestamps[:] = [t for t in timestamps if now - t <= interval]

        if len(timestamps) <= max_messages:
            return

        timestamps.clear()

        try:
            await message.channel.purge(
                limit=max_messages + 5,
                check=lambda m: m.author.id == member.id,
            )
        except discord.HTTPException:
            pass

        try:
            await member.timeout(timedelta(seconds=timeout_seconds), reason="Antispam automatique")
            timeout_ok = True
        except discord.HTTPException:
            timeout_ok = False

        add_sanction(
            member.id,
            f"Mute ({timeout_seconds}s)",
            "Antispam automatique",
            self.bot.user.id,
        )

        detail = f"Spam détecté — mute {timeout_seconds}s" if timeout_ok else "Spam détecté — mute impossible (permissions)"
        await send_mod_log(message.guild, build_log_embed("🚨 Antispam", self.bot.user, member, detail, COLOR_WARN))

        try:
            warn_msg = await message.channel.send(f"🚨 {member.mention} a été mis en silence pour spam.")
            await warn_msg.delete(delay=5)
        except discord.HTTPException:
            pass

    async def _handle_anti_invite(self, message: discord.Message, cfg: dict):
        member = message.author
        if self._is_exempt(member):
            return

        match = INVITE_REGEX.search(message.content)
        if not match:
            return

        code = match.group(1)
        try:
            invite = await self.bot.fetch_invite(code)
            if invite.guild and invite.guild.id == message.guild.id:
                return  # invitation vers ce serveur-ci, on laisse passer
        except (discord.NotFound, discord.HTTPException):
            pass  # invitation invalide/expirée -> on supprime quand même par précaution

        try:
            await message.delete()
        except discord.HTTPException:
            pass

        add_sanction(member.id, "Warn", "Publicité d'un serveur externe (auto)", self.bot.user.id)
        await send_dm(
            member,
            "Avertissement",
            "Tu as posté un lien d'invitation Discord, ce n'est pas autorisé ici.",
            message.guild.name,
        )

        await send_mod_log(
            message.guild,
            build_log_embed(
                "🚫 Anti-invite",
                self.bot.user,
                member,
                f"Message supprimé : ```{message.content[:200]}```",
                COLOR_DANGER,
            ),
        )

        try:
            warn_msg = await message.channel.send(
                f"🚫 {member.mention}, les liens d'invitation vers d'autres serveurs ne sont pas autorisés ici."
            )
            await warn_msg.delete(delay=5)
        except discord.HTTPException:
            pass

    # ─────────────────────────────────────
    #  ANTI-ALT (comptes trop récents)
    # ─────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        automod = get_automod_config()
        cfg = automod["anti_alt"]
        if not cfg.get("enabled"):
            return

        min_days = cfg.get("min_account_age_days", 7)
        account_age = (datetime.now(timezone.utc) - member.created_at).days
        if account_age >= min_days:
            return

        action = cfg.get("action", "alert")

        embed = discord.Embed(
            title="◈  COMPTE RÉCENT DÉTECTÉ  ◈",
            description=(
                f"{member.mention} vient de rejoindre avec un compte créé il y a "
                f"**{account_age} jour{'s' if account_age > 1 else ''}**.\n"
                f"Seuil configuré : `{min_days}` jour{'s' if min_days > 1 else ''}."
            ),
            color=COLOR_WARN,
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        if action == "kick":
            try:
                await member.kick(reason=f"Anti-alt : compte créé il y a {account_age} jour(s) (< {min_days})")
                embed.add_field(name="◈ Action", value="✅ Membre expulsé automatiquement", inline=False)
                embed.color = COLOR_DANGER
            except discord.HTTPException as e:
                embed.add_field(name="◈ Action", value=f"⚠️ Expulsion impossible : `{e}`", inline=False)
        else:
            embed.add_field(name="◈ Action", value="ℹ️ Alerte envoyée au staff, aucune action automatique", inline=False)

        embed.set_footer(text="AERON • Anti multi-compte", icon_url=AERON_LOGO)
        await send_mod_log(member.guild, embed)


async def setup(bot):
    await bot.add_cog(AutoMod(bot))