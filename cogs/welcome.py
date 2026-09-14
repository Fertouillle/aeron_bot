import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# ─────────────────────────────────────────
#  DA AERON
# ─────────────────────────────────────────

AERON_LOGO = "https://media.discordapp.net/attachments/1081628825798058079/1517942955254747227/logo.png?ex=6a381e0a&is=6a36cc8a&hm=355f5b01ca46bb58ffce952cfa88e82fdcc39d9205525331a623c3a173958aca&=&format=webp&quality=lossless"

COLOR_MAIN    = 0x012248
COLOR_SUCCESS = 0x1A6B3A

CONFIG_FILE = "config.json"

# ─────────────────────────────────────────
#  UTILS
# ─────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"welcome": {"channel_id": None}}

def build_welcome_embed(member: discord.Member) -> discord.Embed:
    embed = discord.Embed(
        title="◈  NOUVELLE TRANSMISSION REÇUE  ◈",
        description=(
            f"**{member.mention} vient de rejoindre la Flotte Aeron.**\n\n"
            "Bienvenue parmi nous, soldat.\n"
            "Prends connaissance du règlement et choisis ta faction.\n"
            "La République compte sur toi."
        ),
        color=COLOR_MAIN,
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(
        name="◈ Identité",
        value=f"{member.mention}",
        inline=True
    )
    embed.add_field(
        name="◈ Membre n°",
        value=f"`{member.guild.member_count}`",
        inline=True
    )
    embed.add_field(
        name="◈ Compte créé le",
        value=f"<t:{int(member.created_at.timestamp())}:D>",
        inline=True
    )
    embed.set_footer(
        text="AERON • Communauté Clone Wars Roleplay",
        icon_url=AERON_LOGO
    )
    return embed

# ─────────────────────────────────────────
#  COG
# ─────────────────────────────────────────

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config     = load_config()
        channel_id = config.get("welcome", {}).get("channel_id")
        if not channel_id:
            return
        channel = member.guild.get_channel(channel_id)
        if not channel:
            return
        await channel.send(embed=build_welcome_embed(member))


async def setup(bot):
    await bot.add_cog(Welcome(bot))