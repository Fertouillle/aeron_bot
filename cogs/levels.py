import discord
import json
import os
import random
import time
from discord.ext import commands, tasks
from discord import app_commands

# ─────────────────────────────────────────
#  DA AERON
# ─────────────────────────────────────────

AERON_LOGO    = "https://media.discordapp.net/attachments/1081628825798058079/1517942955254747227/logo.png?ex=6a381e0a&is=6a36cc8a&hm=355f5b01ca46bb58ffce952cfa88e82fdcc39d9205525331a623c3a173958aca&=&format=webp&quality=lossless"
COLOR_MAIN    = 0x012248
COLOR_SUCCESS = 0x1A6B3A
OWNER_ID      = 219821139910852619

CONFIG_FILE = "config.json"
LEVELS_FILE = "levels.json"

MESSAGE_COOLDOWN   = 60     # secondes entre 2 gains d'XP par message
MESSAGE_XP_MIN     = 15
MESSAGE_XP_MAX     = 25
VOICE_XP_AMOUNT    = 10     # XP gagné toutes les VOICE_XP_INTERVAL minutes en vocal
VOICE_XP_INTERVAL  = 5      # minutes

DEFAULT_LEVELS_CONFIG = {
    "enabled":         False,
    "announce_channel_id": None,
    "rewards":         {},   # {"5": role_id, "10": role_id, ...}
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

def get_levels_config():
    config = load_config()
    cfg = config.get("levels", {})
    for key, value in DEFAULT_LEVELS_CONFIG.items():
        cfg.setdefault(key, value)
    return cfg

def save_levels_config(cfg: dict):
    config = load_config()
    config["levels"] = cfg
    save_config(config)

# ─────────────────────────────────────────
#  UTILS — DONNÉES XP
# ─────────────────────────────────────────

def load_data():
    if os.path.exists(LEVELS_FILE):
        with open(LEVELS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(LEVELS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def xp_for_level(level: int) -> int:
    """XP total nécessaire pour atteindre ce niveau (0 XP pour le niveau 0)."""
    if level <= 0:
        return 0
    return 5 * (level ** 2) + 50 * level + 100

def level_from_xp(xp: int) -> int:
    level = 0
    while xp >= xp_for_level(level + 1):
        level += 1
    return level

def get_user_entry(user_id: int) -> dict:
    data = load_data()
    entry = data.get(str(user_id))
    if entry is None:
        entry = {"xp": 0, "last_message": 0}
    return entry

def add_xp(user_id: int, amount: int) -> tuple[int, int, bool]:
    """Ajoute de l'XP, retourne (ancien_niveau, nouveau_niveau, a_level_up)."""
    data  = load_data()
    entry = data.setdefault(str(user_id), {"xp": 0, "last_message": 0})

    old_level = level_from_xp(entry["xp"])
    entry["xp"] += amount
    new_level = level_from_xp(entry["xp"])

    save_data(data)
    return old_level, new_level, new_level > old_level

# ─────────────────────────────────────────
#  EMBEDS
# ─────────────────────────────────────────

def build_rank_embed(member: discord.Member, entry: dict) -> discord.Embed:
    xp = entry.get("xp", 0)
    level = level_from_xp(xp)
    xp_current_level = xp_for_level(level)
    xp_next_level     = xp_for_level(level + 1)
    progress = xp - xp_current_level
    needed   = xp_next_level - xp_current_level

    bar_length = 20
    filled = int(bar_length * (progress / needed)) if needed else 0
    bar = "█" * filled + "░" * (bar_length - filled)

    embed = discord.Embed(
        title=f"◈  RANG — {member.display_name.upper()}  ◈",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏅 **Niveau :** `{level}`\n"
            f"✨ **XP :** `{xp}`\n"
            f"`{bar}`\n"
            f"`{progress}/{needed}` XP avant le niveau `{level + 1}`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=COLOR_MAIN,
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text="AERON • Niveaux", icon_url=AERON_LOGO)
    return embed

def build_leaderboard_embed(guild: discord.Guild, data: dict) -> discord.Embed:
    ranking = sorted(data.items(), key=lambda kv: kv[1].get("xp", 0), reverse=True)[:10]

    lines = []
    medals = ["🥇", "🥈", "🥉"]
    for i, (user_id, entry) in enumerate(ranking):
        member = guild.get_member(int(user_id))
        name = member.display_name if member else f"Membre inconnu ({user_id})"
        rank_icon = medals[i] if i < 3 else f"`#{i + 1}`"
        level = level_from_xp(entry.get("xp", 0))
        lines.append(f"{rank_icon} **{name}** — Niveau `{level}` (`{entry.get('xp', 0)}` XP)")

    embed = discord.Embed(
        title="◈  CLASSEMENT — TOP 10  ◈",
        description="\n".join(lines) if lines else "*Aucune activité enregistrée pour le moment.*",
        color=COLOR_MAIN,
    )
    embed.set_footer(text="AERON • Niveaux", icon_url=AERON_LOGO)
    return embed

def build_levels_settings_embed(cfg: dict) -> discord.Embed:
    channel_display = f"<#{cfg['announce_channel_id']}>" if cfg['announce_channel_id'] else "Non configuré (pas d'annonce)"
    rewards = cfg.get("rewards", {})
    if rewards:
        rewards_text = "\n".join(f"　　Niveau `{lvl}` → <@&{role_id}>" for lvl, role_id in sorted(rewards.items(), key=lambda kv: int(kv[0])))
    else:
        rewards_text = "　　*Aucune récompense configurée.*"

    embed = discord.Embed(
        title="◈  SETTINGS — NIVEAUX / XP  ◈",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Statut :** {'✅ Activé' if cfg['enabled'] else '❌ Désactivé'}\n"
            f"**Salon d'annonce de level up :** {channel_display}\n\n"
            f"**Récompenses de rôle :**\n{rewards_text}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=COLOR_MAIN,
    )
    embed.set_thumbnail(url=AERON_LOGO)
    embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
    return embed

# ─────────────────────────────────────────
#  SETTINGS — SELECTS
# ─────────────────────────────────────────

class LevelsChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Sélectionne le salon d'annonce des level up...",
            channel_types=[discord.ChannelType.text],
        )

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(self.values[0].id)
        cfg = get_levels_config()
        cfg["announce_channel_id"] = channel.id
        save_levels_config(cfg)

        from cogs.levels import LevelsSettingsView, build_levels_settings_embed
        await interaction.response.edit_message(embed=build_levels_settings_embed(cfg), view=LevelsSettingsView())


class RewardLevelModal(discord.ui.Modal, title="Ajouter une récompense de niveau"):
    level = discord.ui.TextInput(label="Niveau requis", placeholder="5", max_length=4)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            level_value = int(self.level.value)
        except ValueError:
            await interaction.response.send_message("❌ Le niveau doit être un nombre.", ephemeral=True)
            return
        if level_value < 1:
            await interaction.response.send_message("❌ Le niveau doit être supérieur à 0.", ephemeral=True)
            return

        embed = discord.Embed(
            title="◈  RÔLE À ATTRIBUER  ◈",
            description=f"Sélectionne le rôle donné au niveau `{level_value}`.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        view = discord.ui.View(timeout=120)
        view.add_item(RewardRoleSelect(level_value))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class RewardRoleSelect(discord.ui.RoleSelect):
    def __init__(self, level_value: int):
        super().__init__(placeholder="Sélectionne un rôle...")
        self.level_value = level_value

    async def callback(self, interaction: discord.Interaction):
        role = self.values[0]
        cfg = get_levels_config()
        cfg["rewards"][str(self.level_value)] = role.id
        save_levels_config(cfg)

        embed = discord.Embed(
            title="◈  RÉCOMPENSE AJOUTÉE  ◈",
            description=f"✅ Niveau `{self.level_value}` → {role.mention}",
            color=COLOR_SUCCESS,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=None)


class RemoveRewardSelect(discord.ui.Select):
    def __init__(self, rewards: dict, guild: discord.Guild):
        options = []
        for lvl, role_id in sorted(rewards.items(), key=lambda kv: int(kv[0])):
            role = guild.get_role(role_id)
            label = f"Niveau {lvl} — {role.name if role else 'Rôle supprimé'}"
            options.append(discord.SelectOption(label=label[:100], value=lvl))
        super().__init__(placeholder="Sélectionne la récompense à retirer...", options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        level_key = self.values[0]
        cfg = get_levels_config()
        cfg["rewards"].pop(level_key, None)
        save_levels_config(cfg)

        embed = discord.Embed(
            title="◈  RÉCOMPENSE RETIRÉE  ◈",
            description=f"✅ La récompense du niveau `{level_key}` a été retirée.",
            color=COLOR_SUCCESS,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=None)

# ─────────────────────────────────────────
#  SETTINGS — VUE PRINCIPALE
# ─────────────────────────────────────────

class LevelsSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Activer / Désactiver", emoji="🔀", style=discord.ButtonStyle.success)
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = get_levels_config()
        cfg["enabled"] = not cfg["enabled"]
        save_levels_config(cfg)
        await interaction.response.edit_message(embed=build_levels_settings_embed(cfg), view=self)

    @discord.ui.button(label="Salon d'annonce", emoji="📢", style=discord.ButtonStyle.secondary)
    async def set_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SALON D'ANNONCE  ◈",
            description="Sélectionne le salon où annoncer les passages de niveau.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        view = discord.ui.View(timeout=120)
        view.add_item(LevelsChannelSelect())
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Ajouter une récompense", emoji="➕", style=discord.ButtonStyle.secondary)
    async def add_reward(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RewardLevelModal())

    @discord.ui.button(label="Retirer une récompense", emoji="➖", style=discord.ButtonStyle.danger)
    async def remove_reward(self, interaction: discord.Interaction, button: discord.ui.Button):
        cfg = get_levels_config()
        if not cfg["rewards"]:
            await interaction.response.send_message("❌ Aucune récompense configurée.", ephemeral=True)
            return

        embed = discord.Embed(
            title="◈  RETIRER UNE RÉCOMPENSE  ◈",
            description="Sélectionne la récompense à retirer.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        view = discord.ui.View(timeout=120)
        view.add_item(RemoveRewardSelect(cfg["rewards"], interaction.guild))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Retour", emoji="◀️", style=discord.ButtonStyle.danger, row=1)
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

class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._voice_sessions = {}  # user_id -> timestamp de la dernière connexion
        self.voice_xp_loop.start()

    def cog_unload(self):
        self.voice_xp_loop.cancel()

    async def _handle_level_up(self, member: discord.Member, new_level: int):
        cfg = get_levels_config()

        # Attribution d'un éventuel rôle de récompense
        reward_role_id = cfg["rewards"].get(str(new_level))
        if reward_role_id:
            role = member.guild.get_role(reward_role_id)
            if role:
                try:
                    await member.add_roles(role, reason=f"Récompense niveau {new_level}")
                except discord.HTTPException:
                    pass

        if not cfg["announce_channel_id"]:
            return
        channel = member.guild.get_channel(cfg["announce_channel_id"])
        if channel is None:
            return

        embed = discord.Embed(
            title="◈  PASSAGE DE NIVEAU  ◈",
            description=f"🎉 {member.mention} passe au niveau **{new_level}** !",
            color=COLOR_SUCCESS,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="AERON • Niveaux", icon_url=AERON_LOGO)
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None:
            return

        cfg = get_levels_config()
        if not cfg["enabled"]:
            return

        now = time.time()
        entry = get_user_entry(message.author.id)
        if now - entry.get("last_message", 0) < MESSAGE_COOLDOWN:
            return

        data = load_data()
        user_data = data.setdefault(str(message.author.id), {"xp": 0, "last_message": 0})
        user_data["last_message"] = now
        save_data(data)

        amount = random.randint(MESSAGE_XP_MIN, MESSAGE_XP_MAX)
        old_level, new_level, leveled_up = add_xp(message.author.id, amount)

        if leveled_up:
            await self._handle_level_up(message.author, new_level)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
        # Rejoint un vocal (et n'y était pas déjà)
        if after.channel and not before.channel:
            self._voice_sessions[member.id] = time.time()
        # Quitte tous les vocaux
        elif before.channel and not after.channel:
            self._voice_sessions.pop(member.id, None)

    @tasks.loop(minutes=VOICE_XP_INTERVAL)
    async def voice_xp_loop(self):
        cfg = get_levels_config()
        if not cfg["enabled"]:
            return

        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                members = [m for m in vc.members if not m.bot and not (m.voice and (m.voice.self_deaf or m.voice.deaf))]
                if len(members) < 2:
                    continue  # pas d'XP si seul dans le salon
                for member in members:
                    old_level, new_level, leveled_up = add_xp(member.id, VOICE_XP_AMOUNT)
                    if leveled_up:
                        await self._handle_level_up(member, new_level)

    @voice_xp_loop.before_loop
    async def before_voice_xp_loop(self):
        await self.bot.wait_until_ready()

    # ── COMMANDES ──────────────────────────

    @app_commands.command(name="rank", description="Voir ton niveau ou celui d'un membre")
    @app_commands.describe(membre="Le membre dont voir le rang (optionnel)")
    async def rank(self, interaction: discord.Interaction, membre: discord.Member = None):
        target = membre or interaction.user
        entry = get_user_entry(target.id)
        embed = build_rank_embed(target, entry)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Voir le classement des membres les plus actifs")
    async def leaderboard(self, interaction: discord.Interaction):
        data = load_data()
        embed = build_leaderboard_embed(interaction.guild, data)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Levels(bot))