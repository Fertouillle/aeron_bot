import discord
import json
import os
import traceback
from discord.ext import commands
from discord import app_commands
from datetime import datetime

# ─────────────────────────────────────────
#  DA AERON
# ─────────────────────────────────────────

AERON_LOGO = "https://media.discordapp.net/attachments/1081628825798058079/1517942955254747227/logo.png?ex=6a381e0a&is=6a36cc8a&hm=355f5b01ca46bb58ffce952cfa88e82fdcc39d9205525331a623c3a173958aca&=&format=webp&quality=lossless"

COLOR_MAIN    = 0x012248
COLOR_SUCCESS = 0x1A6B3A
COLOR_DANGER  = 0x8B1A1A

OWNER_ID   = 219821139910852619
POLLS_FILE = "polls.json"
CONFIG_FILE = "config.json"

# ─────────────────────────────────────────
#  UTILS
# ─────────────────────────────────────────

def load_polls():
    if os.path.exists(POLLS_FILE):
        with open(POLLS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_polls(data):
    with open(POLLS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def is_staff(member: discord.Member) -> bool:
    return member.id == OWNER_ID or member.guild_permissions.manage_messages

async def send_poll_log(guild: discord.Guild, embed: discord.Embed):
    config     = load_config()
    channel_id = config.get("sondage", {}).get("logs_channel_id")
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        await channel.send(embed=embed)

def build_poll_embed(poll: dict) -> discord.Embed:
    total = sum(len(v) for v in poll["votes"].values())

    embed = discord.Embed(
        title=f"◈  {poll['question'].upper()}  ◈",
        description=poll.get("description", ""),
        color=COLOR_MAIN,
    )

    for option, voters in poll["votes"].items():
        count   = len(voters)
        percent = round((count / total * 100) if total > 0 else 0)
        bars    = "█" * (percent // 10) + "░" * (10 - percent // 10)
        embed.add_field(
            name=f"{option}",
            value=f"`{bars}` **{percent}%** ({count} vote{'s' if count != 1 else ''})",
            inline=False
        )

    embed.add_field(name="◈ Total",     value=f"`{total}` vote{'s' if total != 1 else ''}", inline=True)
    embed.add_field(name="◈ Créé par", value=f"<@{poll['author_id']}>",                    inline=True)
    embed.set_footer(
        text=f"AERON • Sondage  |  {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        icon_url=AERON_LOGO
    )
    return embed

def build_closed_embed(poll: dict) -> discord.Embed:
    total = sum(len(v) for v in poll["votes"].values())
    max_votes = max((len(v) for v in poll["votes"].values()), default=0)

    embed = discord.Embed(
        title=f"◈  {poll['question'].upper()}  ◈",
        description=poll.get("description", ""),
        color=0x2C2F33,
    )

    for option, voters in poll["votes"].items():
        count    = len(voters)
        percent  = round((count / total * 100) if total > 0 else 0)
        bars     = "█" * (percent // 10) + "░" * (10 - percent // 10)
        winner   = count == max_votes and max_votes > 0
        prefix   = "🏆 " if winner else ""
        embed.add_field(
            name=f"{prefix}{option}",
            value=f"`{bars}` **{percent}%** ({count} vote{'s' if count != 1 else ''})",
            inline=False
        )

    embed.add_field(name="◈ Total",     value=f"`{total}` vote{'s' if total != 1 else ''}", inline=True)
    embed.add_field(name="◈ Créé par", value=f"<@{poll['author_id']}>",                    inline=True)
    embed.set_footer(
        text=f"AERON • Sondage clôturé  |  {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        icon_url=AERON_LOGO
    )
    return embed

def build_results_embed(poll: dict) -> discord.Embed:
    total = sum(len(v) for v in poll["votes"].values())

    embed = discord.Embed(
        title=f"◈  RÉSULTATS - {poll['question'].upper()}  ◈",
        color=COLOR_MAIN,
    )
    for option, voter_ids in poll["votes"].items():
        count   = len(voter_ids)
        percent = round((count / total * 100) if total > 0 else 0)
        voters  = ", ".join([f"<@{uid}>" for uid in voter_ids]) if voter_ids else "*Aucun vote*"
        embed.add_field(
            name=f"{option} - {percent}% ({count} vote{'s' if count != 1 else ''})",
            value=voters,
            inline=False
        )
    embed.set_footer(
        text=f"AERON • Résultats  |  Total : {total} votes",
        icon_url=AERON_LOGO
    )
    return embed

# ─────────────────────────────────────────
#  VUE : SONDAGE OUI/NON
# ─────────────────────────────────────────

class PollYesNoView(discord.ui.View):
    def __init__(self, poll_id: str):
        super().__init__(timeout=None)
        self.poll_id = poll_id

    async def vote(self, interaction: discord.Interaction, choice: str):
        polls = load_polls()
        poll  = polls.get(self.poll_id)
        if not poll:
            await interaction.response.send_message("❌ Sondage introuvable.", ephemeral=True)
            return

        user_id = str(interaction.user.id)
        for option in poll["votes"]:
            if user_id in poll["votes"][option]:
                poll["votes"][option].remove(user_id)

        poll["votes"][choice].append(user_id)
        save_polls(polls)

        await interaction.response.edit_message(embed=build_poll_embed(poll), view=self)
        await interaction.followup.send("✅ Vote enregistré !", ephemeral=True)

    @discord.ui.button(label="✅ Oui", style=discord.ButtonStyle.success, custom_id="poll_yes")
    async def vote_yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.vote(interaction, "✅ Oui")

    @discord.ui.button(label="❌ Non", style=discord.ButtonStyle.danger, custom_id="poll_no")
    async def vote_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.vote(interaction, "❌ Non")

    @discord.ui.button(label="Voir les votants", style=discord.ButtonStyle.secondary, custom_id="poll_yesno_voters", emoji="🔍")
    async def see_voters(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Réservé au staff.", ephemeral=True)
            return
        polls = load_polls()
        poll  = polls.get(self.poll_id)
        if not poll:
            await interaction.response.send_message("❌ Sondage introuvable.", ephemeral=True)
            return
        await interaction.response.send_message(embed=build_results_embed(poll), ephemeral=True)

    @discord.ui.button(label="Clore le sondage", style=discord.ButtonStyle.danger, custom_id="poll_yesno_close", emoji="🔒")
    async def close_poll(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Réservé au staff.", ephemeral=True)
            return

        polls = load_polls()
        poll  = polls.get(self.poll_id)
        if not poll:
            await interaction.response.send_message("❌ Sondage introuvable.", ephemeral=True)
            return

        # Désactiver tous les boutons
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=build_closed_embed(poll), view=self)

        # Log
        log_embed = discord.Embed(
            title="🔒 Sondage clôturé",
            color=COLOR_DANGER,
        )
        log_embed.add_field(name="◈ Question",   value=poll["question"],              inline=False)
        log_embed.add_field(name="◈ Clôturé par", value=interaction.user.mention,     inline=True)
        log_embed.add_field(name="◈ Créé par",   value=f"<@{poll['author_id']}>",    inline=True)

        total = sum(len(v) for v in poll["votes"].values())
        for option, voter_ids in poll["votes"].items():
            count   = len(voter_ids)
            percent = round((count / total * 100) if total > 0 else 0)
            log_embed.add_field(
                name=f"{option}",
                value=f"**{percent}%** - {count} vote{'s' if count != 1 else ''}",
                inline=True
            )

        log_embed.set_footer(
            text=f"AERON • {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            icon_url=AERON_LOGO
        )
        await send_poll_log(interaction.guild, log_embed)

# ─────────────────────────────────────────
#  VUE : SONDAGE CHOIX MULTIPLES
# ─────────────────────────────────────────

class PollChoiceSelect(discord.ui.Select):
    def __init__(self, poll_id: str, options: list):
        self.poll_id = poll_id
        super().__init__(
            placeholder="[ SÉLECTIONNER UNE OPTION ]",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label=opt, value=opt) for opt in options],
            custom_id=f"poll_choice_{poll_id}"
        )

    async def callback(self, interaction: discord.Interaction):
        polls   = load_polls()
        poll    = polls.get(self.poll_id)
        choice  = self.values[0]
        user_id = str(interaction.user.id)

        if not poll:
            await interaction.response.send_message("❌ Sondage introuvable.", ephemeral=True)
            return

        for option in poll["votes"]:
            if user_id in poll["votes"][option]:
                poll["votes"][option].remove(user_id)

        poll["votes"][choice].append(user_id)
        save_polls(polls)

        await interaction.response.edit_message(
            embed=build_poll_embed(poll),
            view=PollChoiceView(self.poll_id, list(poll["votes"].keys()))
        )
        await interaction.followup.send(f"✅ Vote enregistré pour **{choice}** !", ephemeral=True)


class PollChoiceView(discord.ui.View):
    def __init__(self, poll_id: str, options: list):
        super().__init__(timeout=None)
        self.poll_id = poll_id
        self.add_item(PollChoiceSelect(poll_id, options))

    @discord.ui.button(label="Voir les votants", style=discord.ButtonStyle.secondary, custom_id="poll_choice_voters", emoji="🔍")
    async def see_voters(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Réservé au staff.", ephemeral=True)
            return
        polls = load_polls()
        poll  = polls.get(self.poll_id)
        if not poll:
            await interaction.response.send_message("❌ Sondage introuvable.", ephemeral=True)
            return
        await interaction.response.send_message(embed=build_results_embed(poll), ephemeral=True)

    @discord.ui.button(label="Clore le sondage", style=discord.ButtonStyle.danger, custom_id="poll_choice_close", emoji="🔒")
    async def close_poll(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Réservé au staff.", ephemeral=True)
            return

        polls = load_polls()
        poll  = polls.get(self.poll_id)
        if not poll:
            await interaction.response.send_message("❌ Sondage introuvable.", ephemeral=True)
            return

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(embed=build_closed_embed(poll), view=self)

        # Log
        log_embed = discord.Embed(
            title="🔒 Sondage clôturé",
            color=COLOR_DANGER,
        )
        log_embed.add_field(name="◈ Question",    value=poll["question"],           inline=False)
        log_embed.add_field(name="◈ Clôturé par", value=interaction.user.mention,   inline=True)
        log_embed.add_field(name="◈ Créé par",    value=f"<@{poll['author_id']}>",  inline=True)

        total = sum(len(v) for v in poll["votes"].values())
        for option, voter_ids in poll["votes"].items():
            count   = len(voter_ids)
            percent = round((count / total * 100) if total > 0 else 0)
            log_embed.add_field(
                name=f"{option}",
                value=f"**{percent}%** - {count} vote{'s' if count != 1 else ''}",
                inline=True
            )

        log_embed.set_footer(
            text=f"AERON • {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            icon_url=AERON_LOGO
        )
        await send_poll_log(interaction.guild, log_embed)


# ─────────────────────────────────────────
#  COG PRINCIPAL
# ─────────────────────────────────────────

class Sondage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._restore_views()

    def _restore_views(self):
        polls = load_polls()
        for poll_id, poll in polls.items():
            if poll["type"] == "yesno":
                self.bot.add_view(PollYesNoView(poll_id))
            else:
                self.bot.add_view(PollChoiceView(poll_id, list(poll["votes"].keys())))

    @app_commands.command(name="sondage", description="Créer un sondage")
    @app_commands.describe(
        type="Type de sondage",
        question="Le titre du sondage",
        description="La description ou contexte du sondage",
        options="Options séparées par des virgules (choix multiples uniquement)"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="Oui / Non",        value="yesno"),
        app_commands.Choice(name="Choix multiples",  value="choix"),
    ])
    async def sondage(self, interaction: discord.Interaction, type: str, question: str, description: str = None, options: str = None):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Tu n'as pas accès à cette commande.", ephemeral=True)
            return

        poll_id = f"{interaction.guild_id}-{int(datetime.now().timestamp())}"

        if type == "yesno":
            votes = {"✅ Oui": [], "❌ Non": []}
            view  = PollYesNoView(poll_id)
        else:
            if not options:
                await interaction.response.send_message(
                    "❌ Tu dois fournir des options séparées par des virgules.",
                    ephemeral=True
                )
                return
            opt_list = [o.strip() for o in options.split(",") if o.strip()][:5]
            if len(opt_list) < 2:
                await interaction.response.send_message("❌ Il faut au moins 2 options.", ephemeral=True)
                return
            votes = {opt: [] for opt in opt_list}
            view  = PollChoiceView(poll_id, opt_list)

        poll = {
            "type":        type,
            "question":    question,
            "description": description or "",
            "author_id":   interaction.user.id,
            "votes":       votes,
        }

        polls = load_polls()
        polls[poll_id] = poll
        save_polls(polls)

        await interaction.response.send_message(embed=build_poll_embed(poll), view=view)


async def setup(bot):
    await bot.add_cog(Sondage(bot))