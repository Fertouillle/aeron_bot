import discord
import json
import os
import asyncio
import traceback
import io
from datetime import datetime
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

# ─────────────────────────────────────────
#  TYPES DE TICKETS
# ─────────────────────────────────────────

TICKETS_CONFIG = {
    "aide": {
        "label": "Aide / Question",
        "emoji": "❓",
        "description": "Besoin d'aide ou une question ?",
        "color": COLOR_MAIN,
        "message": (
            "**Bienvenue dans le support AERON.**\n\n"
            "Décris ton problème ou ta question avec le plus de détails possible.\n"
            "Un membre du staff te répondra dans les plus brefs délais.\n\n"
            "*- Équipe AERON*"
        ),
    },
    "deban": {
        "label": "Demande de déban",
        "emoji": "🔓",
        "description": "Contester un bannissement",
        "color": COLOR_WARN,
        "message": (
            "**Demande de réintégration - AERON.**\n\n"
            "Merci de renseigner les informations suivantes :\n"
            "› Ton pseudo au moment du bannissement\n"
            "› La raison supposée du bannissement\n"
            "› Les arguments en faveur de ta réintégration\n\n"
            "*- Équipe AERON*"
        ),
    },
    "plainte": {
        "label": "Plainte",
        "emoji": "⚠️",
        "description": "Signaler un joueur ou un staff",
        "color": COLOR_DANGER,
        "message": (
            "**Dépôt de plainte - AERON.**\n\n"
            "Merci de renseigner les informations suivantes :\n"
            "› Pseudo du joueur ou staff concerné\n"
            "› Description précise des faits\n"
            "› Preuves disponibles (captures d'écran, vidéos)\n\n"
            "*- Équipe AERON*"
        ),
    },
    "recrutement": {
        "label": "Recrutement",
        "emoji": "📋",
        "description": "Rejoindre l'équipe AERON",
        "color": COLOR_SUCCESS,
        "message": (
            "**Candidature - Équipe AERON.**\n\n"
            "Tu souhaites rejoindre nos rangs.\n"
            "Présente-toi et explique ce que tu peux apporter à la communauté.\n"
            "Notre équipe étudiera ta candidature avec attention.\n\n"
            "*- Équipe AERON*"
        ),
    },
    "partenariat": {
        "label": "Partenariat",
        "emoji": "🤝",
        "description": "Proposer un partenariat",
        "color": 0x4B0082,
        "message": (
            "**Proposition de partenariat - AERON.**\n\n"
            "Tu souhaites établir un partenariat avec notre communauté.\n"
            "Présente ton serveur ou projet ainsi que ta proposition.\n"
            "Nous reviendrons vers toi rapidement.\n\n"
            "*- Équipe AERON*"
        ),
    },
    "bug": {
        "label": "Signalement de bug",
        "emoji": "🐛",
        "description": "Signaler un bug ou dysfonctionnement",
        "color": COLOR_WARN,
        "message": (
            "**Rapport de bug - AERON.**\n\n"
            "Merci de renseigner les informations suivantes :\n"
            "› Ce que tu faisais au moment du bug\n"
            "› Ce qui s'est produit\n"
            "› Comment reproduire le bug\n"
            "› Captures d'écran si possible\n\n"
            "*- Équipe AERON*"
        ),
    },
}

# ─────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────

CONFIG_FILE  = "config.json"
COUNTER_FILE = "tickets_count.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"tickets": {"logs_channel_id": None, "roles": {k: [] for k in TICKETS_CONFIG}}}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_next_ticket_number():
    if os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {"count": 0}
    data["count"] += 1
    with open(COUNTER_FILE, "w") as f:
        json.dump(data, f)
    return data["count"]

# ─────────────────────────────────────────
#  UTILS
# ─────────────────────────────────────────

async def get_or_create_category(guild: discord.Guild) -> discord.CategoryChannel:
    category = discord.utils.get(guild.categories, name="Tickets Ouverts")
    if not category:
        category = await guild.create_category("Tickets Ouverts")
    return category

async def send_log(guild: discord.Guild, embed: discord.Embed, file=None):
    config = load_config()
    log_channel_id = config["tickets"].get("logs_channel_id")
    if not log_channel_id:
        return
    channel = guild.get_channel(log_channel_id)
    if channel:
        if file:
            await channel.send(embed=embed, file=file)
        else:
            await channel.send(embed=embed)

async def generate_transcript(channel: discord.TextChannel) -> io.StringIO:
    lines = [f"=== TRANSCRIPT - {channel.name} ===\n"]
    async for message in channel.history(limit=500, oldest_first=True):
        timestamp = message.created_at.strftime("%d/%m/%Y %H:%M")
        content   = message.content or "[embed/fichier]"
        lines.append(f"[{timestamp}] {message.author.display_name} : {content}")
    return io.StringIO("\n".join(lines))

def build_panel_embed() -> discord.Embed:
    embed = discord.Embed(
        title="◈  SUPPORT AERON  ◈",
        description=(
            "**Bienvenue au support de la communauté AERON.**\n"
            "Sélectionne le type de requête dans le menu ci-dessous.\n"
            "Notre équipe traitera ta demande dans les plus brefs délais.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "❓  **Aide / Question** - Une question sur le serveur\n"
            "🔓  **Déban** - Contester un bannissement\n"
            "⚠️  **Plainte** - Signaler un joueur ou un staff\n"
            "📋  **Recrutement** - Rejoindre l'équipe\n"
            "🤝  **Partenariat** - Proposer un partenariat\n"
            "🐛  **Bug** - Signaler un dysfonctionnement\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "*Un seul ticket par catégorie autorisé simultanément.*"
        ),
        color=COLOR_MAIN,
    )
    embed.set_thumbnail(url=AERON_LOGO)
    embed.set_footer(text="AERON • Système de support", icon_url=AERON_LOGO)
    return embed

# ─────────────────────────────────────────
#  VUE : TICKET FERMÉ (Enregistrer / Réouvrir / Supprimer)
# ─────────────────────────────────────────

class ClosedTicketView(discord.ui.View):
    def __init__(self, member_id: int, ticket_type: str, number: int):
        super().__init__(timeout=None)
        self.member_id   = member_id
        self.ticket_type = ticket_type
        self.number      = number

    @discord.ui.button(
        label="Enregistrer le transcript",
        style=discord.ButtonStyle.secondary,
        custom_id="save_transcript",
        emoji="📄"
    )
    async def save_transcript(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        transcript_io   = await generate_transcript(interaction.channel)
        transcript_file = discord.File(
            fp=transcript_io,
            filename=f"transcript-AERON-{self.number:04d}.txt"
        )

        log_embed = discord.Embed(
            title="📄 Transcript enregistré",
            color=COLOR_MAIN,
        )
        log_embed.add_field(name="◈ Référence", value=f"`AERON-{self.number:04d}`", inline=True)
        log_embed.add_field(name="◈ Type", value=TICKETS_CONFIG[self.ticket_type]["label"], inline=True)
        log_embed.add_field(name="◈ Enregistré par", value=interaction.user.mention, inline=True)
        log_embed.set_footer(
            text=f"AERON • {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            icon_url=AERON_LOGO
        )

        await send_log(interaction.guild, log_embed, file=transcript_file)

        button.disabled = True
        button.label    = "Transcript enregistré"
        await interaction.edit_original_response(view=self)

        confirm_embed = discord.Embed(
            description="✅ Transcript enregistré dans les logs.",
            color=COLOR_SUCCESS,
        )
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)

    @discord.ui.button(
        label="Réouvrir le ticket",
        style=discord.ButtonStyle.success,
        custom_id="reopen_ticket",
        emoji="🔓"
    )
    async def reopen_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.guild.get_member(self.member_id)
        if member:
            await interaction.channel.set_permissions(
                member,
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        reopen_embed = discord.Embed(
            title="◈ TICKET RÉOUVERT",
            description=(
                f"Ticket réouvert par {interaction.user.mention}.\n"
                f"{member.mention if member else 'Le membre'} a de nouveau accès au salon."
            ),
            color=COLOR_SUCCESS,
        )
        reopen_embed.set_footer(text="AERON • Système de support", icon_url=AERON_LOGO)

        await interaction.response.edit_message(
            embed=reopen_embed,
            view=TicketActionsView(self.member_id, self.ticket_type, self.number)
        )

    @discord.ui.button(
        label="Supprimer le ticket",
        style=discord.ButtonStyle.danger,
        custom_id="delete_ticket",
        emoji="🗑️"
    )
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Log de suppression
        log_embed = discord.Embed(
            title="🗑️ Ticket supprimé",
            color=COLOR_DANGER,
        )
        log_embed.add_field(name="◈ Référence", value=f"`AERON-{self.number:04d}`", inline=True)
        log_embed.add_field(name="◈ Type", value=TICKETS_CONFIG[self.ticket_type]["label"], inline=True)
        log_embed.add_field(name="◈ Supprimé par", value=interaction.user.mention, inline=True)
        log_embed.add_field(name="◈ Membre", value=f"<@{self.member_id}>", inline=True)
        log_embed.set_footer(
            text=f"AERON • {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            icon_url=AERON_LOGO
        )
        await send_log(interaction.guild, log_embed)

        delete_embed = discord.Embed(
            title="TRANSMISSION TERMINÉE",
            description="Salon supprimé dans **3 secondes**.",
            color=COLOR_DANGER,
        )
        delete_embed.set_footer(text="AERON • Système de support", icon_url=AERON_LOGO)
        await interaction.response.send_message(embed=delete_embed)
        await asyncio.sleep(3)
        await interaction.channel.delete()

# ─────────────────────────────────────────
#  VUE : TICKET OUVERT (Claim + Fermer)
# ─────────────────────────────────────────

class TicketActionsView(discord.ui.View):
    def __init__(self, member_id: int, ticket_type: str, number: int):
        super().__init__(timeout=None)
        self.member_id   = member_id
        self.ticket_type = ticket_type
        self.number      = number

    @discord.ui.button(
        label="Prendre en charge",
        style=discord.ButtonStyle.success,
        custom_id="claim_ticket",
        emoji="🎖️"
    )
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        button.label    = f"Pris en charge par {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)

        claim_embed = discord.Embed(
            title="◈ TICKET PRIS EN CHARGE",
            description=f"{interaction.user.mention} prend en charge cette requête.",
            color=COLOR_SUCCESS,
        )
        claim_embed.set_footer(text="AERON • Système de support", icon_url=AERON_LOGO)
        await interaction.channel.send(embed=claim_embed)

    @discord.ui.button(
        label="Fermer le ticket",
        style=discord.ButtonStyle.danger,
        custom_id="close_ticket",
        emoji="🔒"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Retirer l'accès au membre
        member = interaction.guild.get_member(self.member_id)
        if member:
            await interaction.channel.set_permissions(
                member,
                view_channel=False,
                send_messages=False
            )

        closed_embed = discord.Embed(
            title="🔒 TICKET FERMÉ",
            description=(
                f"Ticket fermé par {interaction.user.mention}.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Choisissez une action ci-dessous."
            ),
            color=COLOR_DANGER,
        )
        closed_embed.add_field(name="📄 Enregistrer", value="Sauvegarder le transcript dans les logs", inline=False)
        closed_embed.add_field(name="🔓 Réouvrir", value="Rendre l'accès au membre et reprendre", inline=False)
        closed_embed.add_field(name="🗑️ Supprimer", value="Supprimer définitivement le salon", inline=False)
        closed_embed.set_footer(text="AERON • Système de support", icon_url=AERON_LOGO)

        await interaction.response.send_message(
            embed=closed_embed,
            view=ClosedTicketView(self.member_id, self.ticket_type, self.number)
        )

# ─────────────────────────────────────────
#  MENU DE SÉLECTION
# ─────────────────────────────────────────

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=config["label"],
                value=key,
                description=config["description"],
                emoji=config["emoji"],
            )
            for key, config in TICKETS_CONFIG.items()
        ]
        super().__init__(
            placeholder="[ SÉLECTIONNER LE TYPE DE REQUÊTE ]",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)

            ticket_type = self.values[0]
            config      = TICKETS_CONFIG[ticket_type]
            guild       = interaction.guild
            member      = interaction.user

            # Ticket déjà ouvert ?
            existing = discord.utils.get(
                guild.text_channels,
                topic=f"ticket-{ticket_type}-{member.id}"
            )
            if existing:
                await interaction.followup.send(
                    f"⚠️ Tu as déjà un ticket de ce type ouvert : {existing.mention}",
                    ephemeral=True
                )
                return

            number      = get_next_ticket_number()
            ticket_name = f"{ticket_type}-{number:04d}"
            category    = await get_or_create_category(guild)

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                member: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True
                ),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, manage_channels=True
                ),
            }

            config_data = load_config()
            for role_id in config_data["tickets"]["roles"].get(ticket_type, []):
                role = guild.get_role(role_id)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=True, read_message_history=True
                    )

            channel = await guild.create_text_channel(
                name=ticket_name,
                category=category,
                overwrites=overwrites,
                topic=f"ticket-{ticket_type}-{member.id}",
            )

            embed = discord.Embed(
                title=f"[ REQUÊTE #{number:04d} - {config['label'].upper()} ]",
                description=config["message"],
                color=config["color"],
            )
            embed.add_field(name="◈ Demandeur", value=member.mention, inline=True)
            embed.add_field(name="◈ Type", value=f"{config['emoji']} {config['label']}", inline=True)
            embed.add_field(name="◈ Référence", value=f"`AERON-{number:04d}`", inline=True)
            embed.set_thumbnail(url=AERON_LOGO)
            embed.set_footer(
                text="AERON • Système de support  |  Utilisez les boutons ci-dessous",
                icon_url=AERON_LOGO
            )

            config_data  = load_config()
            role_mentions = " ".join([
                f"<@&{role_id}>"
                for role_id in config_data["tickets"]["roles"].get(ticket_type, [])
            ])
            mentions = f"{member.mention} {role_mentions}".strip()

            await channel.send(
                content=mentions,
                embed=embed,
                view=TicketActionsView(member.id, ticket_type, number),
            )

            await interaction.followup.send(
                f"✅ Ta requête a été ouverte : {channel.mention}",
                ephemeral=True
            )

            # Réinitialiser le menu pour permettre une nouvelle sélection
            await interaction.message.edit(view=TicketSelectView())

        except Exception as e:
            print(f"❌ ERREUR TICKET : {e}")
            traceback.print_exc()
            try:
                await interaction.followup.send(f"❌ Erreur : `{e}`", ephemeral=True)
            except discord.HTTPException:
                pass


class TicketSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# ─────────────────────────────────────────
#  COG PRINCIPAL
# ─────────────────────────────────────────

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(TicketSelectView())

    # Le déploiement du panel se fait désormais via /settings → Système de tickets → Envoyer le panel


async def setup(bot):
    await bot.add_cog(Tickets(bot))