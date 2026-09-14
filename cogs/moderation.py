import discord
import json
import os
from datetime import datetime
from discord.ext import commands
from discord import app_commands

# ─────────────────────────────────────────
#  DA AERON
# ─────────────────────────────────────────

AERON_LOGO  = "https://media.discordapp.net/attachments/1081628825798058079/1517942955254747227/logo.png?ex=6a381e0a&is=6a36cc8a&hm=355f5b01ca46bb58ffce952cfa88e82fdcc39d9205525331a623c3a173958aca&=&format=webp&quality=lossless"
COLOR_MAIN  = 0x012248
COLOR_DANGER = 0x8B1A1A
COLOR_WARN  = 0xB8860B
COLOR_SUCCESS = 0x1A6B3A
OWNER_ID    = 219821139910852619
CONFIG_FILE = "config.json"
SANCTIONS_FILE = "sanctions.json"

# ─────────────────────────────────────────
#  UTILS
# ─────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def load_sanctions():
    if os.path.exists(SANCTIONS_FILE):
        with open(SANCTIONS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_sanctions(data):
    with open(SANCTIONS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def add_sanction(user_id: int, type: str, reason: str, moderator_id: int):
    sanctions = load_sanctions()
    key = str(user_id)
    if key not in sanctions:
        sanctions[key] = []
    sanctions[key].append({
        "type":         type,
        "reason":       reason,
        "moderator_id": moderator_id,
        "date":         datetime.now().strftime("%d/%m/%Y %H:%M"),
    })
    save_sanctions(sanctions)

async def send_mod_log(guild: discord.Guild, embed: discord.Embed):
    config = load_config()
    channel_id = config.get("moderation", {}).get("logs_channel_id")
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        await channel.send(embed=embed)

def has_mod_permission(interaction: discord.Interaction, command: str) -> bool:
    if interaction.user.id == OWNER_ID:
        return True
    if interaction.user.guild_permissions.administrator:
        return True
    config   = load_config()
    role_ids = config.get("moderation", {}).get("roles", {}).get(command, [])
    user_role_ids = [r.id for r in interaction.user.roles]
    return any(r in user_role_ids for r in role_ids)

async def send_dm(member: discord.Member, action: str, reason: str, guild_name: str):
    try:
        embed = discord.Embed(
            title=f"◈  SANCTION - {action.upper()}  ◈",
            description=(
                f"Tu as reçu une sanction sur **{guild_name}**.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=COLOR_DANGER,
        )
        embed.add_field(name="◈ Action",  value=action,  inline=True)
        embed.add_field(name="◈ Raison",  value=reason,  inline=True)
        embed.set_footer(text="AERON • Modération", icon_url=AERON_LOGO)
        await member.send(embed=embed)
    except discord.HTTPException:
        pass  # DM fermés

def build_log_embed(action: str, moderator: discord.Member, target: discord.Member | str, reason: str, color: int) -> discord.Embed:
    embed = discord.Embed(
        title=f"◈  {action.upper()}  ◈",
        color=color,
    )
    target_value = target.mention if isinstance(target, discord.Member) else target
    embed.add_field(name="◈ Membre",      value=target_value,       inline=True)
    embed.add_field(name="◈ Modérateur",  value=moderator.mention,  inline=True)
    embed.add_field(name="◈ Raison",      value=reason,             inline=False)
    embed.set_footer(
        text=f"AERON • Modération  |  {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        icon_url=AERON_LOGO
    )
    return embed

# ─────────────────────────────────────────
#  HISTORIQUE UTILS
# ─────────────────────────────────────────

SANCTION_CATEGORIES = {
    "résumé":      "📊 Résumé",
    "warn":        "⚠️ Warns",
    "kick":        "👢 Kicks",
    "ban":         "🔨 Bans",
    "mute":        "🔇 Mutes",
}

def filter_by_category(sanctions: list, category: str) -> list:
    if category == "warn":
        return [s for s in sanctions if s["type"] == "Warn"]
    elif category == "kick":
        return [s for s in sanctions if s["type"] == "Kick"]
    elif category == "ban":
        return [s for s in sanctions if s["type"] == "Ban"]
    elif category == "mute":
        return [s for s in sanctions if s["type"].startswith("Mute")]
    return sanctions

def build_historique_embed(membre: discord.Member, sanctions: list, category: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"◈  DOSSIER - {membre.display_name.upper()}  ◈",
        color=COLOR_MAIN,
    )
    embed.set_thumbnail(url=membre.display_avatar.url)

    if category == "résumé":
        warns  = [s for s in sanctions if s["type"] == "Warn"]
        kicks  = [s for s in sanctions if s["type"] == "Kick"]
        bans   = [s for s in sanctions if s["type"] == "Ban"]
        mutes  = [s for s in sanctions if s["type"].startswith("Mute")]

        embed.description = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ **Warns** - `{len(warns)}` sanction{'s' if len(warns) > 1 else ''}{'  •  Dernier : ' + warns[-1]['date'] if warns else ''}\n"
            f"👢 **Kicks** - `{len(kicks)}` sanction{'s' if len(kicks) > 1 else ''}{'  •  Dernier : ' + kicks[-1]['date'] if kicks else ''}\n"
            f"🔨 **Bans** - `{len(bans)}` sanction{'s' if len(bans) > 1 else ''}{'  •  Dernier : ' + bans[-1]['date'] if bans else ''}\n"
            f"🔇 **Mutes** - `{len(mutes)}` sanction{'s' if len(mutes) > 1 else ''}{'  •  Dernier : ' + mutes[-1]['date'] if mutes else ''}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Total : `{len(sanctions)}` sanction{'s' if len(sanctions) > 1 else ''}**"
        )
    else:
        filtered = filter_by_category(sanctions, category)
        if not filtered:
            embed.description = f"*Aucune sanction de type **{SANCTION_CATEGORIES[category]}**.*"
        else:
            embed.description = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            for i, s in enumerate(reversed(filtered[-10:]), 1):
                embed.add_field(
                    name=f"{SANCTION_CATEGORIES[category]} #{i}  •  {s['date']}",
                    value=f"**Raison :** {s['reason']}\n**Modérateur :** <@{s['moderator_id']}>",
                    inline=False
                )
            embed.set_footer(
                text=f"AERON • {len(filtered)} sanction{'s' if len(filtered) > 1 else ''}  |  10 dernières affichées",
                icon_url=AERON_LOGO
            )

    if category == "résumé":
        embed.set_footer(text="AERON • Dossier membre", icon_url=AERON_LOGO)

    return embed


class HistoriqueSelect(discord.ui.Select):
    def __init__(self, membre: discord.Member, sanctions: list):
        self.membre    = membre
        self.sanctions = sanctions
        options = [
            discord.SelectOption(label=label, value=key, emoji=label.split()[0])
            for key, label in SANCTION_CATEGORIES.items()
        ]
        super().__init__(
            placeholder="[ SÉLECTIONNER UNE CATÉGORIE ]",
            options=options,
            custom_id="historique_select"
        )

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        embed    = build_historique_embed(self.membre, self.sanctions, category)
        await interaction.response.edit_message(embed=embed, view=HistoriqueView(self.membre, self.sanctions))


class HistoriqueView(discord.ui.View):
    def __init__(self, membre: discord.Member, sanctions: list):
        super().__init__(timeout=120)
        self.add_item(HistoriqueSelect(membre, sanctions))

# ─────────────────────────────────────────
#  COG PRINCIPAL
# ─────────────────────────────────────────

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── WARN ──────────────────────────────

    @app_commands.command(name="warn", description="Avertir un membre")
    @app_commands.describe(membre="Le membre à avertir", raison="La raison de l'avertissement")
    async def warn(self, interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison fournie"):
        if not has_mod_permission(interaction, "warn"):
            await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
            return
        if membre.id == interaction.user.id:
            await interaction.response.send_message("❌ Tu ne peux pas te sanctionner toi-même.", ephemeral=True)
            return

        add_sanction(membre.id, "Warn", raison, interaction.user.id)
        await send_dm(membre, "Avertissement", raison, interaction.guild.name)

        sanctions = load_sanctions()
        total_warns = len([s for s in sanctions.get(str(membre.id), []) if s["type"] == "Warn"])

        embed = discord.Embed(
            title="◈  AVERTISSEMENT ÉMIS  ◈",
            description=f"{membre.mention} a reçu un avertissement. (**{total_warns}** warn{'s' if total_warns > 1 else ''} au total)",
            color=COLOR_WARN,
        )
        embed.add_field(name="◈ Raison", value=raison, inline=False)
        embed.set_footer(text="AERON • Modération", icon_url=AERON_LOGO)
        await interaction.response.send_message(embed=embed)

        await send_mod_log(interaction.guild, build_log_embed("⚠️ Warn", interaction.user, membre, raison, COLOR_WARN))

    # ── KICK ──────────────────────────────

    @app_commands.command(name="kick", description="Expulser un membre")
    @app_commands.describe(membre="Le membre à expulser", raison="La raison de l'expulsion")
    async def kick(self, interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison fournie"):
        if not has_mod_permission(interaction, "kick"):
            await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
            return
        if membre.id == interaction.user.id:
            await interaction.response.send_message("❌ Tu ne peux pas te sanctionner toi-même.", ephemeral=True)
            return
        if membre.top_role >= interaction.user.top_role and interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Tu ne peux pas sanctionner ce membre.", ephemeral=True)
            return

        add_sanction(membre.id, "Kick", raison, interaction.user.id)
        await send_dm(membre, "Expulsion (Kick)", raison, interaction.guild.name)
        await membre.kick(reason=raison)

        embed = discord.Embed(
            title="◈  MEMBRE EXPULSÉ  ◈",
            description=f"{membre.mention} a été expulsé du serveur.",
            color=COLOR_DANGER,
        )
        embed.add_field(name="◈ Raison", value=raison, inline=False)
        embed.set_footer(text="AERON • Modération", icon_url=AERON_LOGO)
        await interaction.response.send_message(embed=embed)

        await send_mod_log(interaction.guild, build_log_embed("👢 Kick", interaction.user, membre, raison, COLOR_DANGER))

    # ── BAN ───────────────────────────────

    @app_commands.command(name="ban", description="Bannir un membre")
    @app_commands.describe(membre="Le membre à bannir", raison="La raison du bannissement")
    async def ban(self, interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison fournie"):
        if not has_mod_permission(interaction, "ban"):
            await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
            return
        if membre.id == interaction.user.id:
            await interaction.response.send_message("❌ Tu ne peux pas te sanctionner toi-même.", ephemeral=True)
            return
        if membre.top_role >= interaction.user.top_role and interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Tu ne peux pas sanctionner ce membre.", ephemeral=True)
            return

        add_sanction(membre.id, "Ban", raison, interaction.user.id)
        await send_dm(membre, "Bannissement", raison, interaction.guild.name)
        await membre.ban(reason=raison)

        embed = discord.Embed(
            title="◈  MEMBRE BANNI  ◈",
            description=f"{membre.mention} a été banni du serveur.",
            color=COLOR_DANGER,
        )
        embed.add_field(name="◈ Raison", value=raison, inline=False)
        embed.set_footer(text="AERON • Modération", icon_url=AERON_LOGO)
        await interaction.response.send_message(embed=embed)

        await send_mod_log(interaction.guild, build_log_embed("🔨 Ban", interaction.user, membre, raison, COLOR_DANGER))

    # ── UNBAN ─────────────────────────────
    @app_commands.command(name="unban", description="Débannir un membre")
    @app_commands.describe(user_id="L'ID du membre à débannir", raison="La raison du débannissement")
    async def unban(self, interaction: discord.Interaction, user_id: str, raison: str = "Aucune raison fournie"):
        if not has_mod_permission(interaction, "unban"):
            await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
            return

        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user, reason=raison)
            add_sanction(user.id, "Unban", raison, interaction.user.id)
            await send_dm(user, "Débannissement", raison, interaction.guild.name)

            embed = discord.Embed(
                title="◈  MEMBRE DÉBANNI  ◈",
                description=f"**{user}** a été débanni du serveur.",
                color=COLOR_SUCCESS,
            )
            embed.add_field(name="◈ Raison", value=raison, inline=False)
            embed.set_footer(text="AERON • Modération", icon_url=AERON_LOGO)
            await interaction.response.send_message(embed=embed)

            await send_mod_log(interaction.guild, build_log_embed("✅ Unban", interaction.user, str(user), raison, COLOR_SUCCESS))

        except discord.NotFound:
            await interaction.response.send_message("❌ Membre introuvable ou non banni.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ ID invalide.", ephemeral=True)

    # ── MUTE ──────────────────────────────

    @app_commands.command(name="mute", description="Rendre muet un membre")
    @app_commands.describe(
        membre="Le membre à rendre muet",
        duree="Durée en minutes (0 = indéfini)",
        raison="La raison du mute"
    )
    async def mute(self, interaction: discord.Interaction, membre: discord.Member, duree: int = 0, raison: str = "Aucune raison fournie"):
        try:
            if not has_mod_permission(interaction, "mute"):
                await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
                return
            if membre.id == interaction.user.id:
                await interaction.response.send_message("❌ Tu ne peux pas te sanctionner toi-même.", ephemeral=True)
                return
            if membre.top_role >= interaction.user.top_role and interaction.user.id != OWNER_ID:
                await interaction.response.send_message("❌ Tu ne peux pas sanctionner ce membre.", ephemeral=True)
                return

            from datetime import timedelta
            timeout_duration = timedelta(minutes=duree) if duree > 0 else timedelta(days=28)
            await membre.timeout(timeout_duration, reason=raison)

            duree_str = f"{duree} minute{'s' if duree > 1 else ''}" if duree > 0 else "Indéfini"
            add_sanction(membre.id, f"Mute ({duree_str})", raison, interaction.user.id)
            await send_dm(membre, f"Mute ({duree_str})", raison, interaction.guild.name)

            embed = discord.Embed(
                title="◈  MEMBRE RÉDUIT AU SILENCE  ◈",
                description=f"{membre.mention} a été rendu muet.",
                color=COLOR_WARN,
            )
            embed.add_field(name="◈ Durée",  value=duree_str, inline=True)
            embed.add_field(name="◈ Raison", value=raison,    inline=True)
            embed.set_footer(text="AERON • Modération", icon_url=AERON_LOGO)
            await interaction.response.send_message(embed=embed)

            await send_mod_log(interaction.guild, build_log_embed("🔇 Mute", interaction.user, membre, f"{raison} (Durée: {duree_str})", COLOR_WARN))

        except Exception as e:
            print(f"❌ ERREUR MUTE : {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.response.send_message(f"❌ Erreur : `{e}`", ephemeral=True)
            except discord.HTTPException:
                await interaction.followup.send(f"❌ Erreur : `{e}`", ephemeral=True)

    # ── UNMUTE ────────────────────────────

    # ── UNMUTE ────────────────────────────

    @app_commands.command(name="unmute", description="Retirer le mute d'un membre")
    @app_commands.describe(membre="Le membre à unmute", raison="La raison du unmute")
    async def unmute(self, interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison fournie"):
        if not has_mod_permission(interaction, "unmute"):
            await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
            return

        await membre.timeout(None, reason=raison)
        add_sanction(membre.id, "Unmute", raison, interaction.user.id)
        await send_dm(membre, "Démute", raison, interaction.guild.name)

        embed = discord.Embed(
            title="◈  MEMBRE DÉMUTE  ◈",
            description=f"{membre.mention} peut de nouveau parler.",
            color=COLOR_SUCCESS,
        )
        embed.add_field(name="◈ Raison", value=raison, inline=False)
        embed.set_footer(text="AERON • Modération", icon_url=AERON_LOGO)
        await interaction.response.send_message(embed=embed)

        await send_mod_log(interaction.guild, build_log_embed("🔊 Unmute", interaction.user, membre, raison, COLOR_SUCCESS))

    # ── HISTORIQUE ────────────────────────

    @app_commands.command(name="historique", description="Voir l'historique de tes sanctions ou celles d'un membre")
    @app_commands.describe(membre="Le membre dont voir l'historique (staff uniquement)")
    async def historique(self, interaction: discord.Interaction, membre: discord.Member = None):

        # En MP - uniquement son propre historique
        if interaction.guild is None:
            target = interaction.user
            sanctions     = load_sanctions()
            user_sanctions = [s for s in sanctions.get(str(target.id), []) if s["type"] in ("Warn", "Kick", "Ban") or s["type"].startswith("Mute")]
            embed = build_historique_embed(target, user_sanctions, "résumé")
            await interaction.response.send_message(embed=embed, view=HistoriqueView(target, user_sanctions))
            return

        # En serveur - son propre historique sans argument
        if membre is None:
            target = interaction.user
            sanctions      = load_sanctions()
            user_sanctions = [s for s in sanctions.get(str(target.id), []) if s["type"] in ("Warn", "Kick", "Ban") or s["type"].startswith("Mute")]
            embed = build_historique_embed(target, user_sanctions, "résumé")
            await interaction.response.send_message(embed=embed, view=HistoriqueView(target, user_sanctions), ephemeral=True)
            return

        # En serveur avec @membre - staff uniquement
        if not has_mod_permission(interaction, "warn"):
            await interaction.response.send_message("❌ Tu n'as pas la permission de voir les sanctions des autres membres.", ephemeral=True)
            return

        sanctions      = load_sanctions()
        user_sanctions = [s for s in sanctions.get(str(membre.id), []) if s["type"] in ("Warn", "Kick", "Ban") or s["type"].startswith("Mute")]
        embed = build_historique_embed(membre, user_sanctions, "résumé")
        await interaction.response.send_message(embed=embed, view=HistoriqueView(membre, user_sanctions), ephemeral=True)

    # ── SANCTIONS CLEAR ───────────────────

    @app_commands.command(name="sanctions-clear", description="Effacer l'historique des sanctions d'un membre")
    @app_commands.describe(membre="Le membre dont effacer l'historique")
    async def sanctions_clear(self, interaction: discord.Interaction, membre: discord.Member):
        if not has_mod_permission(interaction, "warn"):
            await interaction.response.send_message("❌ Tu n'as pas la permission.", ephemeral=True)
            return

        sanctions = load_sanctions()
        sanctions[str(membre.id)] = []
        save_sanctions(sanctions)

        embed = discord.Embed(
            title="◈  SANCTIONS EFFACÉES  ◈",
            description=f"L'historique de {membre.mention} a été réinitialisé.",
            color=COLOR_SUCCESS,
        )
        embed.set_footer(text="AERON • Modération", icon_url=AERON_LOGO)
        await interaction.response.send_message(embed=embed, ephemeral=True)

        await send_mod_log(interaction.guild, build_log_embed(
            "🗑️ Sanctions Clear", interaction.user, membre, "Historique réinitialisé", COLOR_WARN
        ))


async def setup(bot):
    await bot.add_cog(Moderation(bot))