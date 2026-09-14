import discord
import json
import os
import asyncio
import struct
from discord.ext import commands

# ─────────────────────────────────────────
#  DA AERON
# ─────────────────────────────────────────

OWNER_ID = 219821139910852619

AERON_LOGO    = "https://media.discordapp.net/attachments/1081628825798058079/1517942955254747227/logo.png?ex=6a381e0a&is=6a36cc8a&hm=355f5b01ca46bb58ffce952cfa88e82fdcc39d9205525331a623c3a173958aca&=&format=webp&quality=lossless"
COLOR_MAIN    = 0x012248
COLOR_SUCCESS = 0x1A6B3A
COLOR_WARN    = 0xB8860B
COLOR_DANGER  = 0x8B1A1A

CONFIG_FILE = "config.json"

# ─────────────────────────────────────────
#  TEMPLATES DE COMMANDES
#  Modifiable ici uniquement (dépend de SAM / de la config serveur)
# ─────────────────────────────────────────

RCON_COMMANDS = {
    "say":       'say {message}',
    "changemap": 'changelevel {map}',
    "kick":      'sam kick "{player}" "{reason}"',
    "ban":       'sam ban "{player}" {duration} "{reason}"',
}

# ─────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_rcon_config() -> dict:
    config = load_config()
    default = {"ip": None, "port": 27015, "logs_channel_id": None}
    default.update(config.get("rcon", {}))
    default.pop("password", None)  # le mot de passe ne vit jamais dans config.json
    default["password"] = os.getenv("RCON_PASSWORD", "")
    return default

def save_rcon_config(cfg: dict):
    config = load_config()
    cfg = dict(cfg)
    cfg.pop("password", None)  # jamais persisté sur disque / dans Git
    config["rcon"] = cfg
    save_config(config)

# ─────────────────────────────────────────
#  CLIENT RCON (protocole Source, TCP)
# ─────────────────────────────────────────

SERVERDATA_AUTH        = 3
SERVERDATA_EXECCOMMAND = 2


class RconError(Exception):
    pass


class RconClient:
    def __init__(self, ip: str, port: int, password: str, timeout: float = 5.0):
        self.ip = ip
        self.port = port
        self.password = password
        self.timeout = timeout
        self.reader = None
        self.writer = None
        self._req_id = 0

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    async def connect(self):
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.ip, self.port), timeout=self.timeout
            )
        except (OSError, asyncio.TimeoutError) as e:
            raise RconError(f"Connexion impossible ({self.ip}:{self.port}) : `{e}`")

        await self._send(SERVERDATA_AUTH, self.password)
        resp_id, _ = await self._recv()

        # Le serveur renvoie parfois un paquet vide avant la vraie réponse d'auth
        if resp_id == -1:
            try:
                resp_id, _ = await self._recv()
            except RconError:
                pass

        if resp_id == -1:
            raise RconError("Mot de passe RCON invalide.")

    async def _send(self, pkt_type: int, body: str) -> int:
        req_id = self._next_id()
        payload = struct.pack("<ii", req_id, pkt_type) + body.encode("utf-8") + b"\x00\x00"
        packet = struct.pack("<i", len(payload)) + payload
        self.writer.write(packet)
        await self.writer.drain()
        return req_id

    async def _recv(self):
        try:
            size_data = await asyncio.wait_for(self.reader.readexactly(4), timeout=self.timeout)
            size = struct.unpack("<i", size_data)[0]
            data = await asyncio.wait_for(self.reader.readexactly(size), timeout=self.timeout)
        except (asyncio.IncompleteReadError, asyncio.TimeoutError) as e:
            raise RconError(f"Le serveur n'a pas répondu à temps : `{e}`")
        resp_id, _resp_type = struct.unpack("<ii", data[:8])
        body = data[8:-2].decode("utf-8", errors="ignore")
        return resp_id, body

    async def command(self, cmd: str) -> str:
        await self._send(SERVERDATA_EXECCOMMAND, cmd)
        _, body = await self._recv()
        return body

    async def close(self):
        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception:
                pass


def sanitize_rcon_arg(value: str) -> str:
    """Retire les caractères permettant de casser une commande RCON (guillemets, retours à la ligne, séparateurs)."""
    return value.translate(str.maketrans("", "", '"\';\n\r'))


async def run_rcon_command(cmd: str) -> str:
    cfg = get_rcon_config()
    if not cfg.get("ip") or not cfg.get("password"):
        raise RconError("RCON non configuré (adresse ou mot de passe manquant).")

    client = RconClient(cfg["ip"], cfg["port"], cfg["password"])
    try:
        await client.connect()
        return await client.command(cmd)
    finally:
        await client.close()


async def log_rcon_action(bot, author: discord.abc.User, action: str, command: str, result: str):
    cfg = get_rcon_config()
    channel_id = cfg.get("logs_channel_id")
    if not channel_id:
        return

    embed = discord.Embed(
        title="◈  RCON - ACTION EXÉCUTÉE  ◈",
        description=(
            f"👤 **Auteur :** {author.mention}\n"
            f"⚙️ **Action :** {action}\n"
            f"📝 **Commande :** `{command}`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 **Réponse serveur :**\n```\n{(result.strip() if result else 'Aucune réponse')[:900]}\n```"
        ),
        color=COLOR_WARN,
    )
    embed.set_footer(text="AERON • RCON", icon_url=AERON_LOGO)

    for guild in bot.guilds:
        channel = guild.get_channel(channel_id)
        if channel:
            try:
                await channel.send(embed=embed)
            except discord.HTTPException:
                pass
            break

# ─────────────────────────────────────────
#  MODALS - ACTIONS
# ─────────────────────────────────────────

class RconActionModal(discord.ui.Modal):
    """Base commune : exécute la commande, logue, répond en éphémère."""

    action_label = "Action RCON"

    async def build_command(self) -> str:
        raise NotImplementedError

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cmd = await self.build_command()

        try:
            result = await run_rcon_command(cmd)
        except RconError as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"❌ Erreur inattendue : `{e}`", ephemeral=True)
            return

        await log_rcon_action(interaction.client, interaction.user, self.action_label, cmd, result)
        await interaction.followup.send(f"✅ **{self.action_label}** exécuté avec succès.", ephemeral=True)


class SayModal(RconActionModal, title="Message serveur (say)"):
    action_label = "Message serveur"
    message = discord.ui.TextInput(label="Message à diffuser", style=discord.TextStyle.paragraph, max_length=200)

    async def build_command(self) -> str:
        return RCON_COMMANDS["say"].format(message=sanitize_rcon_arg(self.message.value))


class ChangemapModal(RconActionModal, title="Changer de map"):
    action_label = "Changement de map"
    map_name = discord.ui.TextInput(label="Nom exact de la map", placeholder="rp_coruscant_v2", max_length=64)

    async def build_command(self) -> str:
        return RCON_COMMANDS["changemap"].format(map=sanitize_rcon_arg(self.map_name.value))


class KickModal(RconActionModal, title="Kick un joueur"):
    action_label = "Kick"
    player = discord.ui.TextInput(label="Nom ou SteamID du joueur", max_length=64)
    reason = discord.ui.TextInput(label="Raison", required=False, max_length=200)

    async def build_command(self) -> str:
        reason = sanitize_rcon_arg(self.reason.value or "Aucune raison précisée")
        player = sanitize_rcon_arg(self.player.value)
        return RCON_COMMANDS["kick"].format(player=player, reason=reason)


class BanModal(RconActionModal, title="Bannir un joueur"):
    action_label = "Ban"
    player = discord.ui.TextInput(label="Nom ou SteamID du joueur", max_length=64)
    duration = discord.ui.TextInput(label="Durée en minutes (0 = permanent)", default="0", max_length=10)
    reason = discord.ui.TextInput(label="Raison", required=False, max_length=200)

    async def build_command(self) -> str:
        reason = sanitize_rcon_arg(self.reason.value or "Aucune raison précisée")
        player = sanitize_rcon_arg(self.player.value)
        duration = self.duration.value.strip() or "0"
        if not duration.isdigit():
            duration = "0"
        return RCON_COMMANDS["ban"].format(player=player, duration=duration, reason=reason)

# ─────────────────────────────────────────
#  MODAL - CONFIGURATION
# ─────────────────────────────────────────

class RconConfigModal(discord.ui.Modal, title="Configuration RCON"):
    def __init__(self, cfg: dict):
        super().__init__()
        self.ip_input = discord.ui.TextInput(
            label="Adresse IP du serveur", default=cfg.get("ip") or "", max_length=64
        )
        self.port_input = discord.ui.TextInput(
            label="Port RCON", default=str(cfg.get("port") or 27015), max_length=6
        )
        self.add_item(self.ip_input)
        self.add_item(self.port_input)

    async def on_submit(self, interaction: discord.Interaction):
        cfg = get_rcon_config()
        cfg["ip"] = self.ip_input.value.strip()
        try:
            cfg["port"] = int(self.port_input.value.strip())
        except ValueError:
            cfg["port"] = 27015
        save_rcon_config(cfg)

        embed = build_rcon_settings_embed(cfg)
        await interaction.response.edit_message(embed=embed, view=RconSettingsView())

# ─────────────────────────────────────────
#  VUES
# ─────────────────────────────────────────

def build_rcon_settings_embed(cfg: dict) -> discord.Embed:
    ip_line = f"`{cfg['ip']}:{cfg['port']}`" if cfg.get("ip") else "*Non configuré*"
    pwd_line = "`••••••••` (variable d'environnement)" if cfg.get("password") else "❌ *Non défini - ajoute `RCON_PASSWORD` dans les variables d'environnement*"
    logs_line = f"<#{cfg['logs_channel_id']}>" if cfg.get("logs_channel_id") else "*Non configuré*"

    embed = discord.Embed(
        title="◈  RCON - CONFIGURATION  ◈",
        description=(
            f"**Adresse :** {ip_line}\n"
            f"**Mot de passe :** {pwd_line}\n"
            f"**Salon de logs :** {logs_line}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔒 Le mot de passe RCON se configure uniquement via la variable d'environnement "
            "`RCON_PASSWORD` (jamais stocké dans un fichier).\n"
            "⚠️ Le format exact des commandes kick/ban dépend de SAM - "
            "vérifie `RCON_COMMANDS` dans `rcon.py` si ça ne correspond pas à ta config."
        ),
        color=COLOR_MAIN,
    )
    embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
    return embed


class RconLogsChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Sélectionne le salon de logs RCON...",
            channel_types=[discord.ChannelType.text],
        )

    async def callback(self, interaction: discord.Interaction):
        cfg = get_rcon_config()
        cfg["logs_channel_id"] = self.values[0].id
        save_rcon_config(cfg)
        embed = build_rcon_settings_embed(cfg)
        await interaction.response.edit_message(embed=embed, view=RconSettingsView())


class RconSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Adresse / mot de passe", emoji="🔑", style=discord.ButtonStyle.secondary)
    async def set_creds(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = get_rcon_config()
        await interaction.response.send_modal(RconConfigModal(cfg))

    @discord.ui.button(label="Salon de logs", emoji="📋", style=discord.ButtonStyle.secondary)
    async def set_logs(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SALON DE LOGS RCON  ◈",
            description="Sélectionne le salon où seront envoyés les logs des actions RCON.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        view = discord.ui.View(timeout=120)
        view.add_item(RconLogsChannelSelect())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=build_rcon_menu_embed(), view=RconMenuView())


class RconPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Message serveur", emoji="📢", style=discord.ButtonStyle.primary)
    async def say_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SayModal())

    @discord.ui.button(label="Changer de map", emoji="🗺️", style=discord.ButtonStyle.primary)
    async def changemap_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ChangemapModal())

    @discord.ui.button(label="Kick", emoji="👢", style=discord.ButtonStyle.secondary)
    async def kick_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(KickModal())

    @discord.ui.button(label="Ban", emoji="🔨", style=discord.ButtonStyle.danger)
    async def ban_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BanModal())

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.secondary, row=1)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(embed=build_rcon_menu_embed(), view=RconMenuView())


def build_rcon_menu_embed() -> discord.Embed:
    embed = discord.Embed(
        title="◈  CONTRÔLE SERVEUR (RCON)  ◈",
        description=(
            "Pilote le serveur GMod directement depuis Discord.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Sélectionne une option ci-dessous."
        ),
        color=COLOR_MAIN,
    )
    embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
    return embed


class RconMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Panneau de contrôle", emoji="🕹️", style=discord.ButtonStyle.primary)
    async def panel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = get_rcon_config()
        if not cfg.get("ip") or not cfg.get("password"):
            await interaction.response.send_message(
                "❌ Configure d'abord l'adresse et le mot de passe RCON.", ephemeral=True
            )
            return
        embed = discord.Embed(
            title="◈  PANNEAU DE CONTRÔLE  ◈",
            description="Choisis une action à exécuter sur le serveur.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=RconPanelView())

    @discord.ui.button(label="Configurer", emoji="⚙️", style=discord.ButtonStyle.secondary)
    async def config_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = get_rcon_config()
        await interaction.response.edit_message(embed=build_rcon_settings_embed(cfg), view=RconSettingsView())

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

class Rcon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def setup(bot):
    await bot.add_cog(Rcon(bot))