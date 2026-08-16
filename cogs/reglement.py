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
#  EMBEDS DU RÈGLEMENT
# ─────────────────────────────────────────

def build_reglement_embeds() -> list:
    embeds = []

    # ── Introduction
    embed_intro = discord.Embed(
        title="◈  RÈGLEMENT GÉNÉRAL - AERON  ◈",
        description=(
            "Bienvenue sur **Aeron**, serveur Clone Wars RP.\n"
            "Avant de rejoindre la communauté, merci de lire attentivement les règles suivantes.\n"
            "En acceptant ce règlement, tu t'engages à les respecter en toutes circonstances.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        ),
        color=COLOR_MAIN,
    )
    embed_intro.set_thumbnail(url=AERON_LOGO)
    embed_intro.set_footer(text="AERON • Règlement Général", icon_url=AERON_LOGO)
    embeds.append(embed_intro)

    # ── Section 1 : Comportement général
    embed_comportement = discord.Embed(
        title="§1 - Comportement Général",
        description="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        color=COLOR_MAIN,
    )
    embed_comportement.add_field(
        name="1.1 - Respect",
        value="Le respect est obligatoire envers tous les membres, qu'il s'agisse de joueurs ou de staff. Tout comportement irrespectueux, insultant ou discriminatoire sera sanctionné.",
        inline=False
    )
    embed_comportement.add_field(
        name="1.2 - Harcèlement",
        value="Toute forme de harcèlement, de provocation répétée ou de comportement toxique est strictement interdite et entraînera un bannissement immédiat.",
        inline=False
    )
    embed_comportement.add_field(
        name="1.3 - Contenu inapproprié",
        value="Tout contenu à caractère pornographique, violent, raciste, homophobe ou illégal est formellement interdit sur l'ensemble des salons du serveur.",
        inline=False
    )
    embed_comportement.set_footer(text="AERON • Règlement Général", icon_url=AERON_LOGO)
    embeds.append(embed_comportement)

    # ── Section 2 : Règles RP
    embed_rp = discord.Embed(
        title="§2 - Règles Roleplay",
        description="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        color=COLOR_MAIN,
    )
    embed_rp.add_field(
        name="2.1 - Immersion",
        value="Le respect de l'immersion est primordial. Les communications hors-RP doivent rester dans les salons dédiés. Toute rupture d'immersion intentionnelle sera sanctionnée.",
        inline=False
    )
    embed_rp.add_field(
        name="2.2 - RDM (Random Death Match)",
        value="Tuer un joueur sans raison valable ou sans contexte RP est strictement interdit. Chaque action létale doit être justifiée par le scénario en cours.",
        inline=False
    )
    embed_rp.add_field(
        name="2.3 - FailRP",
        value="Tout comportement contraire à la logique du roleplay (FailRP) est interdit. Les joueurs doivent agir conformément à leur rôle et au contexte de la mission.",
        inline=False
    )
    embed_rp.add_field(
        name="2.4 - Metagaming",
        value="L'utilisation d'informations obtenues hors-RP dans le jeu est interdite. Ce que ton personnage ne sait pas, tu ne peux pas l'utiliser.",
        inline=False
    )
    embed_rp.set_footer(text="AERON • Règlement Général", icon_url=AERON_LOGO)
    embeds.append(embed_rp)

    # ── Section 3 : Communication
    embed_comm = discord.Embed(
        title="§3 - Communication",
        description="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        color=COLOR_MAIN,
    )
    embed_comm.add_field(
        name="3.1 - Spam",
        value="Le spam, les messages répétitifs, les mentions abusives (@everyone, @here) et les floods sont interdits dans tous les salons.",
        inline=False
    )
    embed_comm.add_field(
        name="3.2 - Publicité",
        value="Toute publicité pour un autre serveur Discord, site web ou réseau social est interdite sans autorisation préalable du staff.",
        inline=False
    )
    embed_comm.add_field(
        name="3.3 - Langue",
        value="La langue officielle du serveur est le **français**. Merci de communiquer en français dans tous les salons publics.",
        inline=False
    )
    embed_comm.set_footer(text="AERON • Règlement Général", icon_url=AERON_LOGO)
    embeds.append(embed_comm)

    # ── Section 4 : Staff
    embed_staff = discord.Embed(
        title="§4 - Staff & Sanctions",
        description="━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        color=COLOR_MAIN,
    )
    embed_staff.add_field(
        name="4.1 - Décisions du staff",
        value="Les décisions du staff sont définitives. Toute contestation doit se faire via le système de tickets, jamais en public.",
        inline=False
    )
    embed_staff.add_field(
        name="4.2 - Sanctions",
        value="Les sanctions appliquées sont : avertissement, mute temporaire, kick, bannissement temporaire ou définitif selon la gravité de l'infraction.",
        inline=False
    )
    embed_staff.add_field(
        name="4.3 - Usurpation",
        value="Se faire passer pour un membre du staff ou utiliser un pseudo trompeur est strictement interdit et entraîne un bannissement immédiat.",
        inline=False
    )
    embed_staff.set_footer(text="AERON • Règlement Général", icon_url=AERON_LOGO)
    embeds.append(embed_staff)

    # ── Conclusion
    embed_fin = discord.Embed(
        title="◈  ACCEPTATION DU RÈGLEMENT  ◈",
        description=(
            "En cliquant sur le bouton ci-dessous, tu certifies avoir lu et accepté l'intégralité du règlement d'AERON.\n\n"
            "Tout manquement aux règles exposées ci-dessus pourra entraîner des sanctions allant jusqu'au bannissement définitif.\n\n"
            "*- Commandement AERON*"
        ),
        color=COLOR_SUCCESS,
    )
    embed_fin.set_thumbnail(url=AERON_LOGO)
    embed_fin.set_footer(text="AERON • Règlement Général", icon_url=AERON_LOGO)
    embeds.append(embed_fin)

    return embeds

# ─────────────────────────────────────────
#  VUE : BOUTON ACCEPTATION
# ─────────────────────────────────────────

class ReglementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

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
                "Tu as accès à l'ensemble du serveur AERON.\n\n"
                "*- Commandement AERON*"
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