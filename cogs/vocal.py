import discord
import json
import os
import asyncio
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

CONFIG_FILE   = "config.json"
CHANNELS_FILE = "vocal_channels.json"

# ─────────────────────────────────────────
#  UTILS — CONFIG
# ─────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"vocal": {"hub_channel_id": None}}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ─────────────────────────────────────────
#  UTILS — SALONS TEMPORAIRES (persistance)
# ─────────────────────────────────────────

def load_channels():
    if os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_channels(data):
    with open(CHANNELS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ─────────────────────────────────────────
#  EMBED — PANNEAU DE CONTRÔLE
# ─────────────────────────────────────────

def build_panel_embed(owner: discord.Member) -> discord.Embed:
    embed = discord.Embed(
        title="◈  SALON VOCAL — PANNEAU DE CONTRÔLE  ◈",
        description=(
            f"**Propriétaire :** {owner.mention}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🔒 **Verrouiller / Déverrouiller** — Empêche les nouvelles connexions "
            "*(le salon reste visible par tous)*\n"
            "👥 **Limite** — Définit le nombre maximum de connectés\n"
            "✏️ **Renommer** — Change le nom du salon\n"
            "✅ **Autoriser** — Laisse entrer un membre même si le salon est verrouillé\n"
            "🚫 **Retirer accès** — Retire l'accès prioritaire d'un membre\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "*Ce salon est automatiquement supprimé lorsqu'il est vide.*"
        ),
        color=COLOR_MAIN,
    )
    embed.set_footer(text="AERON • Salons vocaux", icon_url=AERON_LOGO)
    return embed

# ─────────────────────────────────────────
#  MODALS
# ─────────────────────────────────────────

class RenameModal(discord.ui.Modal, title="Renommer le salon"):
    name = discord.ui.TextInput(
        label="Nouveau nom",
        placeholder="Vocal de ...",
        max_length=100,
        required=True,
    )

    def __init__(self, channel: discord.VoiceChannel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.channel.edit(name=str(self.name.value))
            await interaction.response.send_message(
                f"✅ Salon renommé en **{self.name.value}**.", ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(f"❌ Erreur : `{e}`", ephemeral=True)


class LimitModal(discord.ui.Modal, title="Définir la limite"):
    limit = discord.ui.TextInput(
        label="Limite (0 = illimité, max 99)",
        placeholder="0",
        max_length=2,
        required=True,
    )

    def __init__(self, channel: discord.VoiceChannel):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = int(self.limit.value)
        except ValueError:
            await interaction.response.send_message("❌ La limite doit être un nombre.", ephemeral=True)
            return

        if value < 0 or value > 99:
            await interaction.response.send_message(
                "❌ La limite doit être comprise entre 0 et 99.", ephemeral=True
            )
            return

        try:
            await self.channel.edit(user_limit=value)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"❌ Erreur : `{e}`", ephemeral=True)
            return

        texte = "illimitée" if value == 0 else str(value)
        await interaction.response.send_message(f"✅ Limite définie sur **{texte}**.", ephemeral=True)

# ─────────────────────────────────────────
#  SELECTS — AUTORISER / RETIRER
# ─────────────────────────────────────────

class AllowUserSelect(discord.ui.UserSelect):
    def __init__(self, channel: discord.VoiceChannel):
        super().__init__(
            placeholder="Sélectionne un ou plusieurs membres à autoriser...",
            min_values=1,
            max_values=10,
        )
        self.channel = channel

    async def callback(self, interaction: discord.Interaction):
        allowed = []
        for member in self.values:
            overwrite = self.channel.overwrites_for(member)
            overwrite.connect = True
            try:
                await self.channel.set_permissions(member, overwrite=overwrite)
                allowed.append(member.mention)
            except discord.HTTPException:
                pass

        if allowed:
            embed = discord.Embed(
                title="◈  MEMBRE(S) AUTORISÉ(S)  ◈",
                description="✅ " + ", ".join(allowed) + " peuvent maintenant rejoindre le salon.",
                color=COLOR_SUCCESS,
            )
        else:
            embed = discord.Embed(
                title="◈  ERREUR  ◈",
                description="❌ Impossible d'autoriser ces membres.",
                color=COLOR_DANGER,
            )
        embed.set_footer(text="AERON • Salons vocaux", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=None)


class AllowUserView(discord.ui.View):
    def __init__(self, channel: discord.VoiceChannel):
        super().__init__(timeout=120)
        self.add_item(AllowUserSelect(channel))


class RevokeUserSelect(discord.ui.UserSelect):
    def __init__(self, channel: discord.VoiceChannel):
        super().__init__(
            placeholder="Sélectionne un ou plusieurs membres à retirer...",
            min_values=1,
            max_values=10,
        )
        self.channel = channel

    async def callback(self, interaction: discord.Interaction):
        revoked = []
        for member in self.values:
            if member in self.channel.overwrites:
                try:
                    await self.channel.set_permissions(member, overwrite=None)
                    revoked.append(member.mention)
                except discord.HTTPException:
                    pass

        if revoked:
            embed = discord.Embed(
                title="◈  ACCÈS RETIRÉ  ◈",
                description="✅ Accès prioritaire retiré pour " + ", ".join(revoked) + ".",
                color=COLOR_WARN,
            )
        else:
            embed = discord.Embed(
                title="◈  AUCUN CHANGEMENT  ◈",
                description="❌ Ces membres n'avaient pas d'accès prioritaire.",
                color=COLOR_DANGER,
            )
        embed.set_footer(text="AERON • Salons vocaux", icon_url=AERON_LOGO)
        await interaction.response.edit_message(embed=embed, view=None)


class RevokeUserView(discord.ui.View):
    def __init__(self, channel: discord.VoiceChannel):
        super().__init__(timeout=120)
        self.add_item(RevokeUserSelect(channel))

# ─────────────────────────────────────────
#  VUE : PANNEAU DE CONTRÔLE DU SALON
# ─────────────────────────────────────────

class VocalControlView(discord.ui.View):
    def __init__(self, channel_id: int, owner_id: int):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.owner_id   = owner_id

    def get_channel(self, interaction: discord.Interaction):
        return interaction.guild.get_channel(self.channel_id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Seul le propriétaire de ce salon peut utiliser ce panneau.", ephemeral=True
            )
            return False
        channel = self.get_channel(interaction)
        if channel is None:
            await interaction.response.send_message("❌ Ce salon n'existe plus.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Verrouiller", emoji="🔒", style=discord.ButtonStyle.secondary)
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = self.get_channel(interaction)
        try:
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            currently_locked = overwrite.connect is False
            overwrite.connect = None if currently_locked else False
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"❌ Erreur : `{e}`", ephemeral=True)
            return

        if currently_locked:
            button.label = "Verrouiller"
            button.emoji = "🔒"
            button.style = discord.ButtonStyle.secondary
        else:
            button.label = "Déverrouiller"
            button.emoji = "🔓"
            button.style = discord.ButtonStyle.success

        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Limite", emoji="👥", style=discord.ButtonStyle.secondary)
    async def limit(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = self.get_channel(interaction)
        await interaction.response.send_modal(LimitModal(channel))

    @discord.ui.button(label="Renommer", emoji="✏️", style=discord.ButtonStyle.secondary)
    async def rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = self.get_channel(interaction)
        await interaction.response.send_modal(RenameModal(channel))

    @discord.ui.button(label="Autoriser", emoji="✅", style=discord.ButtonStyle.success)
    async def allow(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = self.get_channel(interaction)
        embed = discord.Embed(
            title="◈  AUTORISER UN MEMBRE  ◈",
            description=(
                "Sélectionne le ou les membres à autoriser à rejoindre le salon, "
                "même s'il est verrouillé."
            ),
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Salons vocaux", icon_url=AERON_LOGO)
        await interaction.response.send_message(embed=embed, view=AllowUserView(channel), ephemeral=True)

    @discord.ui.button(label="Retirer accès", emoji="🚫", style=discord.ButtonStyle.danger)
    async def revoke(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = self.get_channel(interaction)
        embed = discord.Embed(
            title="◈  RETIRER UN ACCÈS  ◈",
            description="Sélectionne le ou les membres dont tu veux retirer l'accès prioritaire.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Salons vocaux", icon_url=AERON_LOGO)
        await interaction.response.send_message(embed=embed, view=RevokeUserView(channel), ephemeral=True)

# ─────────────────────────────────────────
#  COG PRINCIPAL
# ─────────────────────────────────────────

class Vocal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Petit verrou pour éviter les suppressions/créations en double
        # lors de mouvements rapides entre salons.
        self._locks = {}

    def _get_lock(self, channel_id: int) -> asyncio.Lock:
        if channel_id not in self._locks:
            self._locks[channel_id] = asyncio.Lock()
        return self._locks[channel_id]

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        config = load_config()
        hub_id = config.get("vocal", {}).get("hub_channel_id")

        # ── Le joueur rejoint le salon "Créer votre salon" ──
        if hub_id and after.channel and after.channel.id == hub_id:
            await self.create_temp_channel(member, after.channel)

        # ── Le joueur quitte un salon temporaire : on vérifie s'il est vide ──
        if before.channel:
            channels = load_channels()
            if str(before.channel.id) in channels:
                await self.maybe_delete_temp_channel(before.channel)

    async def create_temp_channel(self, member: discord.Member, hub_channel: discord.VoiceChannel):
        guild = member.guild

        try:
            channel = await guild.create_voice_channel(
                name=f"Vocal de {member.display_name}"[:100],
                category=hub_channel.category,
                bitrate=hub_channel.bitrate,
                reason=f"Salon vocal temporaire pour {member}",
            )
        except discord.HTTPException as e:
            print(f"❌ ERREUR CRÉATION SALON VOCAL : {e}")
            traceback.print_exc()
            return

        channels = load_channels()
        channels[str(channel.id)] = {"owner_id": member.id, "guild_id": guild.id}
        save_channels(channels)

        try:
            await member.move_to(channel, reason="Déplacement vers son salon vocal temporaire")
        except discord.HTTPException as e:
            print(f"❌ ERREUR DÉPLACEMENT : {e}")

        try:
            await channel.send(
                content=member.mention,
                embed=build_panel_embed(member),
                view=VocalControlView(channel.id, member.id),
            )
        except discord.HTTPException as e:
            print(f"❌ ERREUR ENVOI PANNEAU : {e}")

    async def maybe_delete_temp_channel(self, channel: discord.VoiceChannel):
        lock = self._get_lock(channel.id)
        async with lock:
            channels = load_channels()
            if str(channel.id) not in channels:
                return

            # On relit le salon pour avoir la liste de membres à jour.
            fresh = channel.guild.get_channel(channel.id)
            if fresh is None:
                channels.pop(str(channel.id), None)
                save_channels(channels)
                return

            if len(fresh.members) > 0:
                return

            channels.pop(str(channel.id), None)
            save_channels(channels)
            self._locks.pop(channel.id, None)

            try:
                await fresh.delete(reason="Salon vocal temporaire vide")
            except discord.HTTPException as e:
                print(f"❌ ERREUR SUPPRESSION SALON : {e}")


async def setup(bot):
    await bot.add_cog(Vocal(bot))