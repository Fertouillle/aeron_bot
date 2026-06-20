import discord
from discord.ext import commands
from discord import app_commands

# ─────────────────────────────────────────
#  CONFIG — adapte ces valeurs à ton serveur
# ─────────────────────────────────────────

# ID de la catégorie Discord où les salons de tickets seront créés
CATEGORY_ID = 123456789012345678

# Salon où le panneau de tickets sera posté (commande /panel)
PANEL_CHANNEL_ID = 123456789012345678

# Rôles ayant accès selon le type de ticket (remplace par tes vrais IDs)
ROLES = {
    "aide":        [123456789012345678],  # Staff général
    "deban":       [123456789012345678],  # Modération
    "plainte":     [123456789012345678],  # Modération
    "recrutement": [123456789012345678],  # Recruteurs
    "partenariat": [123456789012345678],  # Partenariats
    "bug":         [123456789012345678],  # Développeurs
}

# ─────────────────────────────────────────
#  CONFIGURATION DES CATÉGORIES
# ─────────────────────────────────────────

TICKETS_CONFIG = {
    "aide": {
        "label": "❓ Aide / Question",
        "description": "Besoin d'aide ou une question ?",
        "color": discord.Color.blue(),
        "message": "Bienvenue ! Explique-nous ton problème ou ta question, le staff te répondra dès que possible.",
    },
    "deban": {
        "label": "🔓 Demande de déban",
        "description": "Contester un bannissement",
        "color": discord.Color.orange(),
        "message": "Merci d'indiquer :\n- Ton pseudo au moment du ban\n- La raison supposée\n- Pourquoi tu mérites d'être débanni",
    },
    "plainte": {
        "label": "⚠️ Plainte",
        "description": "Signaler un joueur ou un staff",
        "color": discord.Color.red(),
        "message": "Merci d'indiquer :\n- Le pseudo du joueur concerné\n- Les faits reprochés\n- Des preuves si possible (screenshots)",
    },
    "recrutement": {
        "label": "📋 Recrutement",
        "description": "Rejoindre l'équipe",
        "color": discord.Color.green(),
        "message": "Tu souhaites rejoindre l'équipe ! Présente-toi et explique pourquoi tu voudrais nous rejoindre.",
    },
    "partenariat": {
        "label": "🤝 Partenariat",
        "description": "Proposer un partenariat",
        "color": discord.Color.purple(),
        "message": "Tu souhaites établir un partenariat ! Présente ton serveur/projet et ce que tu proposes.",
    },
    "bug": {
        "label": "🐛 Bug",
        "description": "Signaler un bug",
        "color": discord.Color.yellow(),
        "message": "Merci de décrire le bug :\n- Ce que tu faisais\n- Ce qui s'est passé\n- Comment reproduire le bug",
    },
}

# ─────────────────────────────────────────
#  VUE : MENU DE SÉLECTION
# ─────────────────────────────────────────

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=config["label"],
                value=key,
                description=config["description"],
            )
            for key, config in TICKETS_CONFIG.items()
        ]
        super().__init__(
            placeholder="Sélectionne le type de ticket...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        ticket_type = self.values[0]
        config = TICKETS_CONFIG[ticket_type]
        guild = interaction.guild
        member = interaction.user

        # Vérifier si l'utilisateur a déjà un ticket ouvert
        existing = discord.utils.get(
            guild.text_channels,
            name=f"ticket-{ticket_type}-{member.name.lower()}"
        )
        if existing:
            await interaction.response.send_message(
                f"❌ Tu as déjà un ticket ouvert : {existing.mention}",
                ephemeral=True
            )
            return

        # Récupérer la catégorie
        category = guild.get_channel(CATEGORY_ID)

        # Construire les permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        for role_id in ROLES.get(ticket_type, []):
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True
                )

        # Créer le salon
        channel = await guild.create_text_channel(
            name=f"ticket-{ticket_type}-{member.name}",
            category=category,
            overwrites=overwrites,
            topic=f"Ticket {config['label']} — {member}",
        )

        # Embed de bienvenue
        embed = discord.Embed(
            title=config["label"],
            description=config["message"],
            color=config["color"],
        )
        embed.set_footer(text=f"Ticket de {member} • {ticket_type}")

        await channel.send(
            content=member.mention,
            embed=embed,
            view=CloseTicketView(),
        )

        await interaction.response.send_message(
            f"✅ Ton ticket a été créé : {channel.mention}",
            ephemeral=True
        )


class TicketSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


# ─────────────────────────────────────────
#  VUE : BOUTON FERMER
# ─────────────────────────────────────────

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 Fermer le ticket",
        style=discord.ButtonStyle.danger,
        custom_id="close_ticket"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔒 Ticket fermé",
            description=f"Ticket fermé par {interaction.user.mention}.\nSalon supprimé dans 5 secondes.",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed)
        import asyncio
        await asyncio.sleep(5)
        await interaction.channel.delete()


# ─────────────────────────────────────────
#  COG PRINCIPAL
# ─────────────────────────────────────────

class Tickets(commands.Cog):
    """Système de tickets support"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="panel", description="Envoie le panneau de tickets dans le salon dédié")
    @app_commands.checks.has_permissions(administrator=True)
    async def panel(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(PANEL_CHANNEL_ID)
        if not channel:
            await interaction.response.send_message("❌ Salon panel introuvable.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎫 Support — Ouvrir un ticket",
            description=(
                "Besoin d'aide ? Sélectionne le type de ticket dans le menu ci-dessous.\n\n"
                "❓ **Aide / Question** — Une question sur le serveur\n"
                "🔓 **Déban** — Contester un bannissement\n"
                "⚠️ **Plainte** — Signaler un joueur ou staff\n"
                "📋 **Recrutement** — Rejoindre l'équipe\n"
                "🤝 **Partenariat** — Proposer un partenariat\n"
                "🐛 **Bug** — Signaler un bug"
            ),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="Un seul ticket par catégorie à la fois.")

        await channel.send(embed=embed, view=TicketSelectView())
        await interaction.response.send_message("✅ Panel envoyé !", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Tickets(bot))