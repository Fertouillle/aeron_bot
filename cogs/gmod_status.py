import discord
import json
import os
import asyncio
import traceback
import a2s
from discord.ext import commands, tasks
from discord import app_commands

# ─────────────────────────────────────────
#  DA AERON
# ─────────────────────────────────────────

AERON_LOGO    = "https://media.discordapp.net/attachments/1081628825798058079/1517942955254747227/logo.png?ex=6a381e0a&is=6a36cc8a&hm=355f5b01ca46bb58ffce952cfa88e82fdcc39d9205525331a623c3a173958aca&=&format=webp&quality=lossless"
COLOR_MAIN    = 0x012248
COLOR_SUCCESS = 0x1A6B3A
COLOR_DANGER  = 0x8B1A1A
OWNER_ID      = 219821139910852619
CONFIG_FILE   = "config.json"

DEFAULT_GMOD_STATUS = {
    "enabled":       False,
    "ip":            None,
    "port":          27015,
    "channel_id":    None,
    "message_id":    None,
    "rename_channel_id": None,
}

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

def get_gmod_status_config():
    config = load_config()
    cfg = config.get("gmod_status", {})
    for key, value in DEFAULT_GMOD_STATUS.items():
        cfg.setdefault(key, value)
    return cfg

def save_gmod_status_config(cfg: dict):
    config = load_config()
    config["gmod_status"] = cfg
    save_config(config)

# ─────────────────────────────────────────
#  EMBED
# ─────────────────────────────────────────

def build_status_embed(info=None, error: str = None) -> discord.Embed:
    if error:
        embed = discord.Embed(
            title="◈  SERVEUR GMOD — HORS LIGNE  ◈",
            description=f"❌ Impossible de contacter le serveur.\n`{error}`",
            color=COLOR_DANGER,
        )
        embed.set_footer(text="AERON • Statut serveur", icon_url=AERON_LOGO)
        return embed

    bar_length = 20
    filled = int(bar_length * (info.player_count / info.max_players)) if info.max_players else 0
    bar = "█" * filled + "░" * (bar_length - filled)

    embed = discord.Embed(
        title="◈  SERVEUR GMOD — EN LIGNE  ◈",
        description=(
            f"**{info.server_name}**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🗺️ **Map :** `{info.map_name}`\n"
            f"👥 **Joueurs :** `{info.player_count}/{info.max_players}`\n"
            f"`{bar}`\n"
            f"📶 **Ping :** `{round(info.ping * 1000)} ms`"
        ),
        color=COLOR_SUCCESS,
    )
    embed.set_thumbnail(url=AERON_LOGO)
    embed.set_footer(text="AERON • Statut serveur — actualisé automatiquement", icon_url=AERON_LOGO)
    return embed

# ─────────────────────────────────────────
#  MODALS / SELECTS — SETTINGS
# ─────────────────────────────────────────

class GmodAddressModal(discord.ui.Modal, title="Adresse du serveur GMod"):
    def __init__(self, cfg: dict):
        super().__init__()
        self.ip_input = discord.ui.TextInput(
            label="Adresse IP",
            placeholder="123.45.67.89",
            default=cfg.get("ip") or "",
        )
        self.port_input = discord.ui.TextInput(
            label="Port de requête (query, souvent 27015)",
            default=str(cfg.get("port") or 27015),
            max_length=5,
        )
        self.add_item(self.ip_input)
        self.add_item(self.port_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            port = int(self.port_input.value)
        except ValueError:
            await interaction.response.send_message("❌ Le port doit être un nombre.", ephemeral=True)
            return

        cfg = get_gmod_status_config()
        cfg["ip"]   = str(self.ip_input.value).strip()
        cfg["port"] = port
        save_gmod_status_config(cfg)

        from cogs.gmod_status import GmodStatusSettingsView, build_gmod_settings_embed
        await interaction.response.edit_message(embed=build_gmod_settings_embed(cfg), view=GmodStatusSettingsView())


class GmodChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Sélectionne le salon d'affichage du statut...",
            channel_types=[discord.ChannelType.text],
        )

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(self.values[0].id)
        cfg = get_gmod_status_config()
        cfg["channel_id"] = channel.id
        cfg["message_id"] = None  # un nouveau message sera envoyé dans ce salon
        save_gmod_status_config(cfg)

        from cogs.gmod_status import GmodStatusSettingsView, build_gmod_settings_embed
        await interaction.response.edit_message(embed=build_gmod_settings_embed(cfg), view=GmodStatusSettingsView())


class GmodRenameChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Sélectionne le salon vocal à renommer...",
            channel_types=[discord.ChannelType.voice],
        )

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(self.values[0].id)
        cfg = get_gmod_status_config()
        cfg["rename_channel_id"] = channel.id
        save_gmod_status_config(cfg)

        from cogs.gmod_status import GmodStatusSettingsView, build_gmod_settings_embed
        await interaction.response.edit_message(embed=build_gmod_settings_embed(cfg), view=GmodStatusSettingsView())

# ─────────────────────────────────────────
#  SETTINGS — VUE
# ─────────────────────────────────────────

def build_gmod_settings_embed(cfg: dict) -> discord.Embed:
    channel_display = f"<#{cfg['channel_id']}>" if cfg['channel_id'] else "Non configuré"
    rename_display = f"<#{cfg['rename_channel_id']}>" if cfg.get('rename_channel_id') else "Non configuré"
    embed = discord.Embed(
        title="◈  SETTINGS — STATUT SERVEUR GMOD  ◈",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Statut :** {'✅ Activé' if cfg['enabled'] else '❌ Désactivé'}\n"
            f"**Adresse :** `{cfg['ip'] or 'Non configurée'}:{cfg['port']}`\n"
            f"**Salon d'affichage :** {channel_display}\n"
            f"**Salon renommé (joueurs) :** {rename_display}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "*Le message est actualisé toutes les 2 minutes, "
            "le nom du salon toutes les 10 minutes (limite Discord).*"
        ),
        color=COLOR_MAIN,
    )
    embed.set_thumbnail(url=AERON_LOGO)
    embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
    return embed


class GmodStatusSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Adresse du serveur", emoji="🌐", style=discord.ButtonStyle.secondary)
    async def set_address(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = get_gmod_status_config()
        await interaction.response.send_modal(GmodAddressModal(cfg))

    @discord.ui.button(label="Salon d'affichage", emoji="📺", style=discord.ButtonStyle.secondary)
    async def set_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SALON D'AFFICHAGE  ◈",
            description="Sélectionne le salon où afficher le statut du serveur GMod.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        view = discord.ui.View(timeout=120)
        view.add_item(GmodChannelSelect())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Salon à renommer", emoji="🏷️", style=discord.ButtonStyle.secondary)
    async def set_rename_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SALON À RENOMMER  ◈",
            description=(
                "Sélectionne un salon **vocal** dont le nom affichera le nombre de joueurs "
                "connectés sur le serveur GMod (ex : `🟢 12/64 joueurs`).\n\n"
                "⚠️ Discord limite les renommages à 2 par 10 minutes : la mise à jour se fait "
                "donc toutes les 10 minutes, pas en temps réel."
            ),
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        view = discord.ui.View(timeout=120)
        view.add_item(GmodRenameChannelSelect())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Voir le statut", emoji="🔍", style=discord.ButtonStyle.secondary)
    async def view_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = get_gmod_status_config()
        if not cfg["ip"]:
            await interaction.response.send_message("❌ Aucun serveur GMod n'est configuré.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        cog = interaction.client.get_cog("GmodStatus")
        try:
            info = await cog._query(cfg["ip"], cfg["port"])
            embed = build_status_embed(info=info)
        except Exception as e:
            embed = build_status_embed(error=str(e))
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="Activer / Désactiver", emoji="🔀", style=discord.ButtonStyle.success)
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = get_gmod_status_config()
        if not cfg["ip"] or not cfg["channel_id"]:
            await interaction.response.send_message(
                "❌ Configure d'abord l'adresse et le salon d'affichage.", ephemeral=True
            )
            return
        cfg["enabled"] = not cfg["enabled"]
        save_gmod_status_config(cfg)
        await interaction.response.edit_message(embed=build_gmod_settings_embed(cfg), view=self)

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
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

class GmodStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.refresh_status.start()
        self.rename_channel.start()

    def cog_unload(self):
        self.refresh_status.cancel()
        self.rename_channel.cancel()

    async def _query(self, ip: str, port: int):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: a2s.info((ip, port), timeout=3.0))

    @tasks.loop(minutes=10)
    async def rename_channel(self):
        cfg = get_gmod_status_config()
        if not cfg["enabled"] or not cfg["ip"] or not cfg.get("rename_channel_id"):
            return

        for guild in self.bot.guilds:
            channel = guild.get_channel(cfg["rename_channel_id"])
            if channel is None:
                continue

            try:
                info = await self._query(cfg["ip"], cfg["port"])
                new_name = f"🟢 {info.player_count}/{info.max_players} joueurs"
            except Exception:
                new_name = "🔴 Serveur hors ligne"

            if channel.name != new_name:
                try:
                    await channel.edit(name=new_name)
                except discord.HTTPException as e:
                    print(f"❌ ERREUR RENOMMAGE SALON GMOD : {e}")

            break  # un seul serveur/salon configuré pour l'instant

    @rename_channel.before_loop
    async def before_rename_channel(self):
        await self.bot.wait_until_ready()

    @tasks.loop(minutes=2)
    async def refresh_status(self):
        cfg = get_gmod_status_config()
        if not cfg["enabled"] or not cfg["ip"] or not cfg["channel_id"]:
            return

        for guild in self.bot.guilds:
            channel = guild.get_channel(cfg["channel_id"])
            if channel is None:
                continue

            try:
                info = await self._query(cfg["ip"], cfg["port"])
                embed = build_status_embed(info=info)
            except Exception as e:
                embed = build_status_embed(error=str(e))

            message = None
            if cfg.get("message_id"):
                try:
                    message = await channel.fetch_message(cfg["message_id"])
                except discord.NotFound:
                    message = None
                except discord.HTTPException:
                    message = None

            try:
                if message:
                    await message.edit(embed=embed)
                else:
                    message = await channel.send(embed=embed)
                    cfg["message_id"] = message.id
                    save_gmod_status_config(cfg)
            except discord.HTTPException as e:
                print(f"❌ ERREUR STATUT GMOD : {e}")
                traceback.print_exc()

            break  # un seul serveur/salon configuré pour l'instant

    @refresh_status.before_loop
    async def before_refresh_status(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="gmod-status", description="Voir le statut actuel du serveur GMod")
    async def gmod_status_cmd(self, interaction: discord.Interaction):
        cfg = get_gmod_status_config()
        if not cfg["ip"]:
            await interaction.response.send_message("❌ Aucun serveur GMod n'est configuré.", ephemeral=True)
            return

        await interaction.response.defer()
        try:
            info = await self._query(cfg["ip"], cfg["port"])
            embed = build_status_embed(info=info)
        except Exception as e:
            embed = build_status_embed(error=str(e))
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(GmodStatus(bot))