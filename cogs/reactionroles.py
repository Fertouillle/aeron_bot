import discord
import json
import os
import traceback
from discord.ext import commands

# ─────────────────────────────────────────
#  DA AERON
# ─────────────────────────────────────────

AERON_LOGO    = "https://media.discordapp.net/attachments/1081628825798058079/1517942955254747227/logo.png?ex=6a381e0a&is=6a36cc8a&hm=355f5b01ca46bb58ffce952cfa88e82fdcc39d9205525331a623c3a173958aca&=&format=webp&quality=lossless"
COLOR_MAIN    = 0x012248
COLOR_SUCCESS = 0x1A6B3A
COLOR_WARN    = 0xB8860B
COLOR_DANGER  = 0x8B1A1A

OWNER_ID = 219821139910852619

DATA_FILE = "reaction_roles.json"

# ─────────────────────────────────────────
#  UTILS - PERSISTANCE
# ─────────────────────────────────────────

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def match_role_id(panel: dict, emoji: discord.PartialEmoji):
    emoji_str = str(emoji)
    for entry in panel["roles"]:
        if entry["emoji"] == emoji_str:
            return entry["role_id"]
    return None

# ─────────────────────────────────────────
#  EMBEDS
# ─────────────────────────────────────────

def build_panel_embed(panel: dict) -> discord.Embed:
    lines = [f"{entry['emoji']} - <@&{entry['role_id']}>" for entry in panel["roles"]]
    roles_text = "\n".join(lines) if lines else "*Aucun rôle configuré pour le moment.*"

    parts = []
    if panel.get("description"):
        parts.append(panel["description"])
    parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    parts.append(roles_text)
    if panel.get("unique"):
        parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        parts.append("*Une seule réaction possible parmi ces rôles.*")

    embed = discord.Embed(
        title=f"◈  {panel.get('title', 'RÔLES')}  ◈",
        description="\n".join(parts),
        color=COLOR_MAIN,
    )
    embed.set_footer(text="AERON • Rôles à réaction", icon_url=AERON_LOGO)
    return embed


def build_manage_embed(panel: dict) -> discord.Embed:
    lines = [f"{entry['emoji']} - <@&{entry['role_id']}>" for entry in panel["roles"]]
    roles_text = "\n".join(lines) if lines else "*Aucun rôle configuré.*"

    embed = discord.Embed(
        title=f"◈  GESTION - {panel.get('title', 'PANNEAU').upper()}  ◈",
        description=(
            f"**Rôles configurés :**\n{roles_text}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Mode unique :** {'✅ Activé' if panel.get('unique') else '❌ Désactivé'}\n"
            "*(mode unique = une seule réaction possible parmi ce panneau)*"
        ),
        color=COLOR_MAIN,
    )
    embed.set_footer(text="AERON • Rôles à réaction", icon_url=AERON_LOGO)
    return embed

# ─────────────────────────────────────────
#  RECONSTRUCTION DU MESSAGE (garde l'ordre)
# ─────────────────────────────────────────

async def fetch_panel_message(bot: commands.Bot, message_id: int):
    """Retourne (panel, message) ou (None, message_erreur)."""
    data  = load_data()
    panel = data.get(str(message_id))
    if panel is None:
        return None, None, "Panneau introuvable."

    guild = bot.get_guild(panel["guild_id"])
    if guild is None:
        return None, None, "Serveur introuvable."

    channel = guild.get_channel(panel["channel_id"])
    if channel is None:
        return None, None, "Salon introuvable."

    try:
        message = await channel.fetch_message(message_id)
    except discord.NotFound:
        return None, None, "Le message du panneau a été supprimé manuellement."
    except discord.HTTPException as e:
        return None, None, f"Erreur : `{e}`"

    return panel, message, None


async def update_panel_embed_only(bot: commands.Bot, message_id: int):
    """Met à jour uniquement l'embed, sans toucher aux réactions déjà posées."""
    panel, message, error = await fetch_panel_message(bot, message_id)
    if error:
        return None, error

    try:
        await message.edit(embed=build_panel_embed(panel))
    except discord.HTTPException as e:
        return None, f"Erreur lors de la mise à jour du message : `{e}`"

    return message, None


async def add_role_reaction(bot: commands.Bot, message_id: int, emoji_str: str):
    """Ajoute uniquement la nouvelle réaction, sans retirer celles déjà présentes."""
    panel, message, error = await fetch_panel_message(bot, message_id)
    if error:
        return None, error

    try:
        await message.edit(embed=build_panel_embed(panel))
    except discord.HTTPException as e:
        return None, f"Erreur lors de la mise à jour du message : `{e}`"

    try:
        await message.add_reaction(emoji_str)
    except discord.HTTPException as e:
        return None, f"Emoji invalide ou non ajoutable : `{e}`"

    return message, None


async def remove_role_reaction(bot: commands.Bot, message_id: int, emoji_str: str):
    """Retire uniquement la réaction du rôle supprimé (les autres restent intactes)."""
    panel, message, error = await fetch_panel_message(bot, message_id)
    if error:
        return None, error

    try:
        await message.edit(embed=build_panel_embed(panel))
    except discord.HTTPException as e:
        return None, f"Erreur lors de la mise à jour du message : `{e}`"

    try:
        await message.clear_reaction(discord.PartialEmoji.from_str(emoji_str))
    except discord.HTTPException:
        pass  # l'emoji pouvait déjà ne plus être présent, on ignore

    return message, None


async def rebuild_panel_message(bot: commands.Bot, message_id: int):
    """Reconstruit entièrement l'ordre des réactions (⚠️ efface les réactions de tout le monde).
    À utiliser uniquement pour le réordonnancement."""
    panel, message, error = await fetch_panel_message(bot, message_id)
    if error:
        return None, error

    try:
        await message.edit(embed=build_panel_embed(panel))
    except discord.HTTPException as e:
        return None, f"Erreur lors de la mise à jour du message : `{e}`"

    try:
        await message.clear_reactions()
    except discord.HTTPException:
        pass

    for entry in panel["roles"]:
        try:
            await message.add_reaction(entry["emoji"])
        except discord.HTTPException:
            pass

    return message, None

# ─────────────────────────────────────────
#  MODALS
# ─────────────────────────────────────────

class CreatePanelModal(discord.ui.Modal, title="Créer un panneau de rôles"):
    panel_title = discord.ui.TextInput(
        label="Titre du panneau",
        placeholder="Choisis tes rôles",
        max_length=100,
    )
    panel_description = discord.ui.TextInput(
        label="Description (optionnel)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000,
    )

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="◈  SALON DU PANNEAU  ◈",
            description="Sélectionne le salon où envoyer le panneau de rôles.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Rôles à réaction", icon_url=AERON_LOGO)
        view = discord.ui.View(timeout=180)
        view.add_item(PanelChannelSelect(str(self.panel_title.value), str(self.panel_description.value)))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class AddRoleEmojiModal(discord.ui.Modal, title="Ajouter un rôle"):
    emoji = discord.ui.TextInput(
        label="Emoji à utiliser",
        placeholder="😀 ou <:nom:id>",
        max_length=100,
    )

    def __init__(self, message_id: int):
        super().__init__()
        self.message_id = message_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            partial = discord.PartialEmoji.from_str(str(self.emoji.value).strip())
        except Exception:
            await interaction.response.send_message("❌ Emoji invalide.", ephemeral=True)
            return
        emoji_str = str(partial)

        data  = load_data()
        panel = data.get(str(self.message_id))
        if panel is None:
            await interaction.response.send_message("❌ Ce panneau n'existe plus.", ephemeral=True)
            return
        if any(r["emoji"] == emoji_str for r in panel["roles"]):
            await interaction.response.send_message("❌ Cet emoji est déjà utilisé sur ce panneau.", ephemeral=True)
            return

        embed = discord.Embed(
            title="◈  RÔLE À ASSOCIER  ◈",
            description=f"Sélectionne le rôle à associer à {emoji_str}.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Rôles à réaction", icon_url=AERON_LOGO)
        view = discord.ui.View(timeout=120)
        view.add_item(AddRoleSelect(self.message_id, emoji_str))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class EditPanelModal(discord.ui.Modal, title="Modifier le panneau"):
    def __init__(self, message_id: int, panel: dict):
        super().__init__()
        self.message_id = message_id
        self.panel_title_input = discord.ui.TextInput(
            label="Titre du panneau",
            max_length=100,
            default=panel.get("title", ""),
        )
        self.panel_description_input = discord.ui.TextInput(
            label="Description (optionnel)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
            default=panel.get("description", "") or "",
        )
        self.add_item(self.panel_title_input)
        self.add_item(self.panel_description_input)

    async def on_submit(self, interaction: discord.Interaction):
        data  = load_data()
        panel = data.get(str(self.message_id))
        if panel is None:
            await interaction.response.send_message("❌ Ce panneau n'existe plus.", ephemeral=True)
            return

        panel["title"]       = str(self.panel_title_input.value)
        panel["description"] = str(self.panel_description_input.value)
        save_data(data)

        _, error = await update_panel_embed_only(interaction.client, self.message_id)
        if error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)
            return

        await interaction.response.send_message("✅ Panneau mis à jour.", ephemeral=True)

# ─────────────────────────────────────────
#  SELECTS
# ─────────────────────────────────────────

class PanelChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, title: str, description: str):
        super().__init__(
            placeholder="Sélectionne un salon...",
            channel_types=[discord.ChannelType.text],
        )
        self.title_       = title
        self.description_ = description

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(self.values[0].id)
        panel = {
            "guild_id":    interaction.guild.id,
            "channel_id":  channel.id,
            "title":       self.title_,
            "description": self.description_,
            "unique":      False,
            "roles":       [],
        }
        try:
            message = await channel.send(embed=build_panel_embed(panel))
        except discord.HTTPException as e:
            await interaction.response.edit_message(content=f"❌ Erreur : `{e}`", embed=None, view=None)
            return

        data = load_data()
        data[str(message.id)] = panel
        save_data(data)

        embed = discord.Embed(
            title="◈  PANNEAU CRÉÉ  ◈",
            description=f"✅ Panneau créé dans {channel.mention}.\nAjoute maintenant des rôles ci-dessous.",
            color=COLOR_SUCCESS,
        )
        embed.set_footer(text="AERON • Rôles à réaction", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=ManagePanelView(message.id))


class AddRoleSelect(discord.ui.RoleSelect):
    def __init__(self, message_id: int, emoji_str: str):
        super().__init__(placeholder="Sélectionne un rôle...")
        self.message_id = message_id
        self.emoji_str  = emoji_str

    async def callback(self, interaction: discord.Interaction):
        role  = self.values[0]
        data  = load_data()
        panel = data.get(str(self.message_id))
        if panel is None:
            await interaction.response.edit_message(content="❌ Ce panneau n'existe plus.", embed=None, view=None)
            return
        if any(r["role_id"] == role.id for r in panel["roles"]):
            await interaction.response.edit_message(content="❌ Ce rôle est déjà présent sur ce panneau.", embed=None, view=None)
            return

        panel["roles"].append({"emoji": self.emoji_str, "role_id": role.id})
        save_data(data)

        _, error = await add_role_reaction(interaction.client, self.message_id, self.emoji_str)
        if error:
            panel["roles"].pop()
            save_data(data)
            await interaction.response.edit_message(content=f"❌ {error}", embed=None, view=None)
            return

        embed = discord.Embed(
            title="◈  RÔLE AJOUTÉ  ◈",
            description=f"✅ {self.emoji_str} → {role.mention} ajouté au panneau.",
            color=COLOR_SUCCESS,
        )
        embed.set_footer(text="AERON • Rôles à réaction", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=None)


class RemoveRoleSelect(discord.ui.Select):
    def __init__(self, message_id: int, roles: list, guild: discord.Guild):
        options = []
        for entry in roles:
            role  = guild.get_role(entry["role_id"])
            label = role.name if role else f"Rôle supprimé ({entry['role_id']})"
            option_kwargs = {"label": label[:100], "value": str(entry["role_id"])}
            try:
                option_kwargs["emoji"] = entry["emoji"]
                options.append(discord.SelectOption(**option_kwargs))
            except (discord.errors.InvalidArgument, TypeError, ValueError):
                option_kwargs.pop("emoji", None)
                options.append(discord.SelectOption(**option_kwargs))

        super().__init__(placeholder="Sélectionne le rôle à retirer...", options=options[:25])
        self.message_id = message_id

    async def callback(self, interaction: discord.Interaction):
        role_id = int(self.values[0])
        data    = load_data()
        panel   = data.get(str(self.message_id))
        if panel is None:
            await interaction.response.edit_message(content="❌ Ce panneau n'existe plus.", embed=None, view=None)
            return

        removed_emoji  = next((r["emoji"] for r in panel["roles"] if r["role_id"] == role_id), None)
        panel["roles"] = [r for r in panel["roles"] if r["role_id"] != role_id]
        save_data(data)

        if removed_emoji:
            _, error = await remove_role_reaction(interaction.client, self.message_id, removed_emoji)
        else:
            _, error = await update_panel_embed_only(interaction.client, self.message_id)
        if error:
            await interaction.response.edit_message(content=f"❌ {error}", embed=None, view=None)
            return

        embed = discord.Embed(
            title="◈  RÔLE RETIRÉ  ◈",
            description="✅ Le rôle a été retiré du panneau.",
            color=COLOR_WARN,
        )
        embed.set_footer(text="AERON • Rôles à réaction", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=None)


class ReorderRoleSelect(discord.ui.Select):
    def __init__(self, message_id: int, roles: list, guild: discord.Guild):
        options = []
        for index, entry in enumerate(roles, start=1):
            role  = guild.get_role(entry["role_id"])
            label = f"{index}. {role.name if role else 'Rôle supprimé'}"
            option_kwargs = {"label": label[:100], "value": str(entry["role_id"])}
            try:
                options.append(discord.SelectOption(emoji=entry["emoji"], **option_kwargs))
            except (discord.errors.InvalidArgument, TypeError, ValueError):
                options.append(discord.SelectOption(**option_kwargs))

        super().__init__(placeholder="Sélectionne le rôle à déplacer...", options=options[:25])
        self.message_id = message_id

    async def callback(self, interaction: discord.Interaction):
        role_id = int(self.values[0])
        panel = load_data().get(str(self.message_id))
        if panel is None:
            await interaction.response.edit_message(content="❌ Ce panneau n'existe plus.", embed=None, view=None)
            return

        embed = build_reorder_embed(panel, interaction.guild)
        await interaction.response.edit_message(
            embed=embed, view=ReorderControlView(self.message_id, role_id)
        )


def build_reorder_embed(panel: dict, guild: discord.Guild, highlight_role_id: int = None) -> discord.Embed:
    lines = []
    for index, entry in enumerate(panel["roles"], start=1):
        role = guild.get_role(entry["role_id"])
        name = role.name if role else "Rôle supprimé"
        marker = "➡️ " if entry["role_id"] == highlight_role_id else ""
        lines.append(f"{marker}{index}. {entry['emoji']} - {name}")

    embed = discord.Embed(
        title="◈  RÉORDONNER LES RÔLES  ◈",
        description=(
            "\n".join(lines) if lines else "*Aucun rôle configuré.*"
        ) + "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\nUtilise ⬆️/⬇️ pour déplacer le rôle sélectionné.",
        color=COLOR_MAIN,
    )
    embed.set_footer(text="AERON • Rôles à réaction", icon_url=AERON_LOGO)
    return embed


class ReorderControlView(discord.ui.View):
    def __init__(self, message_id: int, role_id: int):
        super().__init__(timeout=180)
        self.message_id = message_id
        self.role_id    = role_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    async def _move(self, interaction: discord.Interaction, offset: int):
        data  = load_data()
        panel = data.get(str(self.message_id))
        if panel is None:
            await interaction.response.edit_message(content="❌ Ce panneau n'existe plus.", embed=None, view=None)
            return

        roles = panel["roles"]
        index = next((i for i, r in enumerate(roles) if r["role_id"] == self.role_id), None)
        if index is None:
            await interaction.response.edit_message(content="❌ Ce rôle n'est plus dans le panneau.", embed=None, view=None)
            return

        new_index = index + offset
        if new_index < 0 or new_index >= len(roles):
            await interaction.response.defer()
            return

        roles[index], roles[new_index] = roles[new_index], roles[index]
        save_data(data)

        _, error = await rebuild_panel_message(interaction.client, self.message_id)
        if error:
            await interaction.response.edit_message(content=f"❌ {error}", embed=None, view=None)
            return

        embed = build_reorder_embed(panel, interaction.guild, highlight_role_id=self.role_id)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Monter", emoji="⬆️", style=discord.ButtonStyle.secondary)
    async def move_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._move(interaction, -1)

    @discord.ui.button(label="Descendre", emoji="⬇️", style=discord.ButtonStyle.secondary)
    async def move_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._move(interaction, 1)

    @discord.ui.button(label="Terminé", emoji="✅", style=discord.ButtonStyle.success)
    async def done(self, interaction: discord.Interaction, button: discord.ui.Button):
        panel = load_data().get(str(self.message_id))
        if panel is None:
            await interaction.response.edit_message(content="❌ Ce panneau n'existe plus.", embed=None, view=None)
            return
        await interaction.response.edit_message(embed=build_manage_embed(panel), view=ManagePanelView(self.message_id))


class ManagePanelSelect(discord.ui.Select):
    def __init__(self, panels: dict, guild: discord.Guild):
        options = []
        for message_id, panel in panels.items():
            channel = guild.get_channel(panel["channel_id"])
            options.append(discord.SelectOption(
                label=(panel.get("title") or "Panneau")[:90],
                description=f"#{channel.name}" if channel else "Salon introuvable",
                value=message_id,
            ))
        super().__init__(placeholder="Sélectionne un panneau...", options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        message_id = int(self.values[0])
        data  = load_data()
        panel = data.get(str(message_id))
        if panel is None:
            await interaction.response.edit_message(content="❌ Ce panneau n'existe plus.", embed=None, view=None)
            return
        await interaction.response.edit_message(embed=build_manage_embed(panel), view=ManagePanelView(message_id))

# ─────────────────────────────────────────
#  VUE : GESTION D'UN PANNEAU
# ─────────────────────────────────────────

class ManagePanelView(discord.ui.View):
    def __init__(self, message_id: int):
        super().__init__(timeout=180)
        self.message_id = message_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    def get_panel(self):
        data = load_data()
        return data.get(str(self.message_id))

    @discord.ui.button(label="Ajouter un rôle", emoji="➕", style=discord.ButtonStyle.success)
    async def add_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.get_panel() is None:
            await interaction.response.send_message("❌ Ce panneau n'existe plus.", ephemeral=True)
            return
        await interaction.response.send_modal(AddRoleEmojiModal(self.message_id))

    @discord.ui.button(label="Retirer un rôle", emoji="➖", style=discord.ButtonStyle.danger)
    async def remove_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        panel = self.get_panel()
        if not panel or not panel["roles"]:
            await interaction.response.send_message("❌ Aucun rôle à retirer.", ephemeral=True)
            return
        embed = discord.Embed(
            title="◈  RETIRER UN RÔLE  ◈",
            description="Sélectionne le rôle à retirer du panneau.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Rôles à réaction", icon_url=AERON_LOGO)
        view = discord.ui.View(timeout=120)
        view.add_item(RemoveRoleSelect(self.message_id, panel["roles"], interaction.guild))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Modifier le texte", emoji="✏️", style=discord.ButtonStyle.secondary)
    async def edit_text(self, interaction: discord.Interaction, button: discord.ui.Button):
        panel = self.get_panel()
        if panel is None:
            await interaction.response.send_message("❌ Ce panneau n'existe plus.", ephemeral=True)
            return
        await interaction.response.send_modal(EditPanelModal(self.message_id, panel))

    @discord.ui.button(label="Mode unique", emoji="🔀", style=discord.ButtonStyle.secondary)
    async def toggle_unique(self, interaction: discord.Interaction, button: discord.ui.Button):
        data  = load_data()
        panel = data.get(str(self.message_id))
        if panel is None:
            await interaction.response.send_message("❌ Ce panneau n'existe plus.", ephemeral=True)
            return

        panel["unique"] = not panel.get("unique", False)
        save_data(data)

        _, error = await update_panel_embed_only(interaction.client, self.message_id)
        if error:
            await interaction.response.send_message(f"❌ {error}", ephemeral=True)
            return

        state = "activé ✅" if panel["unique"] else "désactivé ❌"
        await interaction.response.send_message(f"Mode unique {state} pour ce panneau.", ephemeral=True)

    @discord.ui.button(label="Réordonner", emoji="↕️", style=discord.ButtonStyle.secondary)
    async def reorder(self, interaction: discord.Interaction, button: discord.ui.Button):
        panel = self.get_panel()
        if not panel or not panel["roles"]:
            await interaction.response.send_message("❌ Aucun rôle à réordonner.", ephemeral=True)
            return
        if len(panel["roles"]) < 2:
            await interaction.response.send_message("❌ Il faut au moins 2 rôles pour réordonner.", ephemeral=True)
            return

        embed = discord.Embed(
            title="◈  RÉORDONNER LES RÔLES  ◈",
            description=(
                "Sélectionne le rôle que tu veux déplacer.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚠️ Discord ne permet pas de déplacer une réaction : à chaque mouvement, "
                "**toutes les réactions du message sont retirées puis remises** dans le "
                "nouvel ordre. Les membres devront re-cliquer pour que leur coche réapparaisse, "
                "mais **ils ne perdent pas les rôles déjà obtenus**."
            ),
            color=COLOR_WARN,
        )
        embed.set_footer(text="AERON • Rôles à réaction", icon_url=AERON_LOGO)
        view = discord.ui.View(timeout=180)
        view.add_item(ReorderRoleSelect(self.message_id, panel["roles"], interaction.guild))
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Supprimer le panneau", emoji="🗑️", style=discord.ButtonStyle.danger, row=1)
    async def delete_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        data  = load_data()
        panel = data.pop(str(self.message_id), None)
        save_data(data)

        if panel:
            channel = interaction.guild.get_channel(panel["channel_id"])
            if channel:
                try:
                    message = await channel.fetch_message(self.message_id)
                    await message.delete()
                except discord.HTTPException:
                    pass

        embed = discord.Embed(
            title="◈  PANNEAU SUPPRIMÉ  ◈",
            description="✅ Le panneau a été supprimé.",
            color=COLOR_WARN,
        )
        embed.set_footer(text="AERON • Rôles à réaction", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=None)

# ─────────────────────────────────────────
#  VUE : MENU PRINCIPAL
# ─────────────────────────────────────────

class ReactionRolesMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Accès refusé.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Créer un panneau", emoji="➕", style=discord.ButtonStyle.success)
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreatePanelModal())

    @discord.ui.button(label="Gérer un panneau existant", emoji="🛠️", style=discord.ButtonStyle.primary)
    async def manage(self, interaction: discord.Interaction, button: discord.ui.Button):
        data   = load_data()
        panels = {mid: p for mid, p in data.items() if p.get("guild_id") == interaction.guild.id}
        if not panels:
            await interaction.response.send_message("❌ Aucun panneau existant sur ce serveur.", ephemeral=True)
            return

        embed = discord.Embed(
            title="◈  GÉRER UN PANNEAU  ◈",
            description="Sélectionne le panneau à modifier.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Rôles à réaction", icon_url=AERON_LOGO)
        view = discord.ui.View(timeout=120)
        view.add_item(ManagePanelSelect(panels, interaction.guild))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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

class ReactionRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return
        if payload.member and payload.member.bot:
            return

        data  = load_data()
        panel = data.get(str(payload.message_id))
        if panel is None:
            return

        role_id = match_role_id(panel, payload.emoji)
        if role_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        role   = guild.get_role(role_id)
        member = payload.member or guild.get_member(payload.user_id)
        if role is None or member is None:
            return

        try:
            if panel.get("unique"):
                other_role_ids = [r["role_id"] for r in panel["roles"] if r["role_id"] != role_id]
                to_remove = [guild.get_role(rid) for rid in other_role_ids]
                to_remove = [r for r in to_remove if r and r in member.roles]
                if to_remove:
                    await member.remove_roles(*to_remove, reason="Rôles à réaction (mode unique)")
                    channel = guild.get_channel(panel["channel_id"])
                    if channel:
                        try:
                            message = await channel.fetch_message(payload.message_id)
                            for entry in panel["roles"]:
                                if entry["role_id"] != role_id:
                                    try:
                                        await message.remove_reaction(entry["emoji"], member)
                                    except discord.HTTPException:
                                        pass
                        except discord.HTTPException:
                            pass

            if role not in member.roles:
                await member.add_roles(role, reason="Rôles à réaction")
        except discord.Forbidden:
            print(f"❌ Permissions insuffisantes pour attribuer un rôle sur {guild.name}")
        except discord.HTTPException as e:
            print(f"❌ ERREUR RÔLE À RÉACTION : {e}")
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return

        data  = load_data()
        panel = data.get(str(payload.message_id))
        if panel is None:
            return

        role_id = match_role_id(panel, payload.emoji)
        if role_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.HTTPException:
                return

        if member.bot:
            return

        role = guild.get_role(role_id)
        if role is None:
            return

        try:
            if role in member.roles:
                await member.remove_roles(role, reason="Retrait réaction - rôles à réaction")
        except discord.Forbidden:
            print(f"❌ Permissions insuffisantes pour retirer un rôle sur {guild.name}")
        except discord.HTTPException as e:
            print(f"❌ ERREUR RÔLE À RÉACTION (remove) : {e}")
            traceback.print_exc()


async def setup(bot):
    await bot.add_cog(ReactionRoles(bot))