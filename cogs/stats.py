import discord
import json
import os
from datetime import datetime
from discord.ext import commands
from discord import app_commands

# ─────────────────────────────────────────
#  DA AERON
# ─────────────────────────────────────────

AERON_LOGO   = "https://media.discordapp.net/attachments/1081628825798058079/1517942955254747227/logo.png?ex=6a381e0a&is=6a36cc8a&hm=355f5b01ca46bb58ffce952cfa88e82fdcc39d9205525331a623c3a173958aca&=&format=webp&quality=lossless"
COLOR_MAIN   = 0x012248

SANCTIONS_FILE = "sanctions.json"
LEVELS_FILE    = "levels.json"


def load_json(path: str) -> dict:
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}


class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stats", description="Voir les statistiques du serveur")
    async def stats(self, interaction: discord.Interaction):
        guild = interaction.guild
        await interaction.response.defer()

        # ── Membres ──
        total_members  = guild.member_count
        online_members = len([m for m in guild.members if m.status != discord.Status.offline])
        bot_count       = len([m for m in guild.members if m.bot])

        # ── Salons vocaux occupés ──
        in_voice = sum(len(vc.members) for vc in guild.voice_channels)

        # ── Tickets ouverts ──
        tickets_category = discord.utils.get(guild.categories, name="Tickets Ouverts")
        tickets_open = len(tickets_category.channels) if tickets_category else 0

        # ── Sanctions ce mois-ci ──
        sanctions = load_json(SANCTIONS_FILE)
        now = datetime.now()
        month_sanctions = 0
        for user_sanctions in sanctions.values():
            for s in user_sanctions:
                try:
                    date = datetime.strptime(s["date"], "%d/%m/%Y %H:%M")
                    if date.month == now.month and date.year == now.year:
                        month_sanctions += 1
                except (ValueError, KeyError):
                    continue

        # ── Membres actifs (niveaux) ──
        levels_data = load_json(LEVELS_FILE)
        active_members = len(levels_data)

        embed = discord.Embed(
            title="◈  STATISTIQUES — AERON  ◈",
            color=COLOR_MAIN,
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else AERON_LOGO)
        embed.add_field(
            name="◈ Membres",
            value=(
                f"👥 Total : `{total_members}`\n"
                f"🟢 En ligne : `{online_members}`\n"
                f"🤖 Bots : `{bot_count}`"
            ),
            inline=True,
        )
        embed.add_field(
            name="◈ Activité",
            value=(
                f"🔊 En vocal : `{in_voice}`\n"
                f"🎫 Tickets ouverts : `{tickets_open}`\n"
                f"🏅 Membres actifs (XP) : `{active_members}`"
            ),
            inline=True,
        )
        embed.add_field(
            name="◈ Modération",
            value=f"⚠️ Sanctions ce mois-ci : `{month_sanctions}`",
            inline=False,
        )
        embed.set_footer(text=f"AERON • Serveur créé le {guild.created_at.strftime('%d/%m/%Y')}", icon_url=AERON_LOGO)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Stats(bot))