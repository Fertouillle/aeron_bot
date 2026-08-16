import discord
import json
import os
import re
from datetime import datetime, timezone, time as dtime
from discord.ext import commands, tasks
from discord import app_commands

# ─────────────────────────────────────────
#  DA AERON
# ─────────────────────────────────────────

AERON_LOGO    = "https://media.discordapp.net/attachments/1081628825798058079/1517942955254747227/logo.png?ex=6a381e0a&is=6a36cc8a&hm=355f5b01ca46bb58ffce952cfa88e82fdcc39d9205525331a623c3a173958aca&=&format=webp&quality=lossless"
COLOR_MAIN    = 0x012248
COLOR_SUCCESS = 0x1A6B3A
OWNER_ID      = 219821139910852619

CONFIG_FILE    = "config.json"
BIRTHDAYS_FILE = "birthdays.json"

DEFAULT_BIRTHDAYS_CONFIG = {
    "channel_id": None,
}

DATE_REGEX = re.compile(r"^([0-3]?\d)[/\-]([01]?\d)$")

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

def get_birthdays_config():
    config = load_config()
    cfg = config.get("birthdays", {})
    for key, value in DEFAULT_BIRTHDAYS_CONFIG.items():
        cfg.setdefault(key, value)
    return cfg

def save_birthdays_config(cfg: dict):
    config = load_config()
    config["birthdays"] = cfg
    save_config(config)

# ─────────────────────────────────────────
#  UTILS — DONNÉES (jour/mois uniquement, pas d'année)
# ─────────────────────────────────────────

def load_data():
    if os.path.exists(BIRTHDAYS_FILE):
        with open(BIRTHDAYS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(BIRTHDAYS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ─────────────────────────────────────────
#  SETTINGS — SELECT SALON
# ─────────────────────────────────────────

class BirthdayChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(
            placeholder="Sélectionne le salon des annonces d'anniversaire...",
            channel_types=[discord.ChannelType.text],
        )

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(self.values[0].id)
        cfg = get_birthdays_config()
        cfg["channel_id"] = channel.id
        save_birthdays_config(cfg)

        from cogs.birthdays import BirthdaysSettingsView, build_birthdays_settings_embed
        await interaction.response.edit_message(embed=build_birthdays_settings_embed(cfg), view=BirthdaysSettingsView())


def build_birthdays_settings_embed(cfg: dict) -> discord.Embed:
    channel_display = f"<#{cfg['channel_id']}>" if cfg['channel_id'] else "Non configuré"
    embed = discord.Embed(
        title="◈  SETTINGS — ANNIVERSAIRES  ◈",
        description=(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Salon d'annonces :** {channel_display}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "*L'anniversaire du serveur est automatique (date de création du serveur Discord).*\n"
            "*Chaque membre peut renseigner sa date de naissance (jour/mois uniquement) avec `/anniversaire definir`.*"
        ),
        color=COLOR_MAIN,
    )
    embed.set_thumbnail(url=AERON_LOGO)
    embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
    return embed


class BirthdaysSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Salon d'annonces", emoji="📢", style=discord.ButtonStyle.secondary)
    async def set_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  SALON D'ANNONCES  ◈",
            description="Sélectionne le salon où annoncer les anniversaires.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Settings", icon_url=AERON_LOGO)
        view = discord.ui.View(timeout=120)
        view.add_item(BirthdayChannelSelect())
        await interaction.response.edit_message(embed=embed, view=view)

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

class Birthdays(commands.Cog):
    group = app_commands.Group(name="anniversaire", description="Gérer ton anniversaire")

    def __init__(self, bot):
        self.bot = bot
        self.daily_check.start()

    def cog_unload(self):
        self.daily_check.cancel()

    @group.command(name="definir", description="Renseigner ta date de naissance (jour/mois uniquement)")
    @app_commands.describe(date="Format JJ/MM, ex: 24/12 (l'année n'est pas demandée)")
    async def definir(self, interaction: discord.Interaction, date: str):
        match = DATE_REGEX.match(date.strip())
        if not match:
            await interaction.response.send_message("❌ Format invalide. Utilise JJ/MM, par exemple `24/12`.", ephemeral=True)
            return

        day, month = int(match.group(1)), int(match.group(2))
        try:
            datetime(2000, month, day)  # année bissextile arbitraire pour valider 29/02
        except ValueError:
            await interaction.response.send_message("❌ Cette date n'existe pas.", ephemeral=True)
            return

        data = load_data()
        data[str(interaction.user.id)] = {"day": day, "month": month}
        save_data(data)

        await interaction.response.send_message(
            f"✅ Anniversaire enregistré : **{day:02d}/{month:02d}** (l'année n'est jamais demandée ni stockée).",
            ephemeral=True,
        )

    @group.command(name="retirer", description="Retirer ta date d'anniversaire enregistrée")
    async def retirer(self, interaction: discord.Interaction):
        data = load_data()
        if str(interaction.user.id) in data:
            del data[str(interaction.user.id)]
            save_data(data)
            await interaction.response.send_message("✅ Ton anniversaire a été retiré.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Tu n'avais aucun anniversaire enregistré.", ephemeral=True)

    @tasks.loop(time=dtime(hour=9, minute=0, tzinfo=timezone.utc))
    async def daily_check(self):
        today = datetime.now(timezone.utc)

        for guild in self.bot.guilds:
            cfg = get_birthdays_config()
            if not cfg["channel_id"]:
                continue
            channel = guild.get_channel(cfg["channel_id"])
            if channel is None:
                continue

            # ── Anniversaire du serveur ──
            created = guild.created_at
            if created.day == today.day and created.month == today.month:
                years = today.year - created.year
                embed = discord.Embed(
                    title="◈  JOYEUX ANNIVERSAIRE, AERON !  ◈",
                    description=f"🎉 Le serveur fête aujourd'hui ses **{years} an{'s' if years > 1 else ''}** !",
                    color=COLOR_SUCCESS,
                )
                embed.set_thumbnail(url=AERON_LOGO)
                embed.set_footer(text="AERON • Anniversaire", icon_url=AERON_LOGO)
                try:
                    await channel.send(embed=embed)
                except discord.HTTPException:
                    pass

            # ── Anniversaires des membres ──
            data = load_data()
            for user_id, entry in data.items():
                if entry["day"] == today.day and entry["month"] == today.month:
                    member = guild.get_member(int(user_id))
                    if member is None:
                        continue
                    embed = discord.Embed(
                        title="◈  JOYEUX ANNIVERSAIRE  ◈",
                        description=f"🎂 Toute l'équipe d'Aeron souhaite un joyeux anniversaire à {member.mention} !",
                        color=COLOR_SUCCESS,
                    )
                    embed.set_thumbnail(url=member.display_avatar.url)
                    embed.set_footer(text="AERON • Anniversaire", icon_url=AERON_LOGO)
                    try:
                        await channel.send(embed=embed)
                    except discord.HTTPException:
                        pass

    @daily_check.before_loop
    async def before_daily_check(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Birthdays(bot))