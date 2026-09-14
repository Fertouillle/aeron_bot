import discord
import json
import os
from discord.ext import commands
from discord import app_commands

# ─────────────────────────────────────────
#  DA AERON
# ─────────────────────────────────────────

AERON_LOGO = "https://media.discordapp.net/attachments/1081628825798058079/1517942955254747227/logo.png?ex=6a381e0a&is=6a36cc8a&hm=355f5b01ca46bb58ffce952cfa88e82fdcc39d9205525331a623c3a173958aca&=&format=webp&quality=lossless"

COLOR_MAIN    = 0x012248
COLOR_SUCCESS = 0x1A6B3A
COLOR_DANGER  = 0x8B1A1A
COLOR_WARN    = 0xB8860B

OWNER_ID    = 219821139910852619
CONFIG_FILE = "config.json"

# ─────────────────────────────────────────
#  UTILS
# ─────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

# ─────────────────────────────────────────
#  EMBED DU RÈGLEMENT
# ─────────────────────────────────────────

def get_reglement_config() -> dict:
    config = load_config()
    return config.get("reglement", {})

def build_reglement_embed() -> discord.Embed:
    doc_url = get_reglement_config().get("doc_url")

    description = (
        "Bienvenue sur **Aeron**, serveur Clone Wars RP.\n\n"
        "Le règlement complet de la communauté est disponible dans le document "
        "ci-dessous. Merci de le lire **attentivement** avant d'accepter - il "
        "s'applique à tous les membres, sans exception.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    if doc_url:
        description += f"📄 **[Lire le règlement complet]({doc_url})**\n\n"
    description += (
        "✅ Une fois la lecture terminée, clique sur **J'ai lu et j'accepte** "
        "ci-dessous pour accéder à l'ensemble du serveur.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    embed = discord.Embed(
        title="◈  RÈGLEMENT GÉNÉRAL - AERON  ◈",
        description=description,
        color=COLOR_MAIN,
    )
    embed.set_thumbnail(url=AERON_LOGO)
    embed.set_footer(text="AERON • Règlement Général", icon_url=AERON_LOGO)
    return embed

# ─────────────────────────────────────────
#  VUE : BOUTONS RÈGLEMENT
# ─────────────────────────────────────────

class ReglementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        doc_url = get_reglement_config().get("doc_url")
        if doc_url:
            self.add_item(discord.ui.Button(
                label="Lire le règlement",
                emoji="📄",
                style=discord.ButtonStyle.link,
                url=doc_url,
            ))

    @discord.ui.button(
        label="J'ai lu et j'accepte le règlement",
        style=discord.ButtonStyle.success,
        custom_id="accept_reglement",
        emoji="✅"
    )
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        config  = load_config()
        role_id = config.get("reglement", {}).get("role_id")

        if not role_id:
            await interaction.response.send_message(
                "❌ Aucun rôle configuré. Contacte un administrateur.",
                ephemeral=True
            )
            return

        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message(
                "❌ Rôle introuvable. Contacte un administrateur.",
                ephemeral=True
            )
            return

        if role in interaction.user.roles:
            await interaction.response.send_message(
                "✅ Tu as déjà accepté le règlement !",
                ephemeral=True
            )
            return

        await interaction.user.add_roles(role)

        embed = discord.Embed(
            title="◈ RÈGLEMENT ACCEPTÉ",
            description=(
                f"Bienvenue parmi nous, {interaction.user.mention} !\n"
                "Tu as accès à l'ensemble du serveur AERON."
            ),
            color=COLOR_SUCCESS,
        )
        embed.set_footer(text="AERON • Règlement Général", icon_url=AERON_LOGO)
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ─────────────────────────────────────────
#  COG PRINCIPAL
# ─────────────────────────────────────────

class Reglement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(ReglementView())

    # L'envoi du règlement se fait via /settings → Règlement → Envoyer le règlement


async def setup(bot):
    await bot.add_cog(Reglement(bot))