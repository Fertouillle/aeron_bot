import discord
import random
import time
import io
from discord.ext import commands, tasks
from discord import app_commands
from PIL import Image, ImageDraw

# ─────────────────────────────────────────
#  DA AERON
# ─────────────────────────────────────────

AERON_LOGO    = "https://media.discordapp.net/attachments/1081628825798058079/1517942955254747227/logo.png?ex=6a381e0a&is=6a36cc8a&hm=355f5b01ca46bb58ffce952cfa88e82fdcc39d9205525331a623c3a173958aca&=&format=webp&quality=lossless"
COLOR_MAIN    = 0x012248
COLOR_SUCCESS = 0x1A6B3A
COLOR_DANGER  = 0x8B1A1A
COLOR_WARN    = 0xB8860B

XP_MORPION_WIN = 15
XP_PENDU_WIN   = 10
HANGMAN_INACTIVITY_LIMIT = 600  # 10 minutes


def award_xp(user_id: int, amount: int):
    """Ajoute de l'XP via le cog Levels, sans casser les jeux si celui-ci est indisponible."""
    try:
        from cogs.levels import add_xp
        add_xp(user_id, amount)
    except Exception:
        pass

# ═════════════════════════════════════════
#  PIERRE / FEUILLE / CISEAUX (1V1)
# ═════════════════════════════════════════

RPS_CHOICES = {
    "pierre":  "🪨",
    "feuille": "📄",
    "ciseaux": "✂️",
}

RPS_BEATS = {
    "pierre":  "ciseaux",
    "feuille": "pierre",
    "ciseaux": "feuille",
}


class RPSMatch:
    def __init__(self, player1: discord.Member, player2: discord.Member):
        self.player1 = player1
        self.player2 = player2
        self.choices = {}
        self.message = None
        self.finished = False

    def both_chosen(self) -> bool:
        return self.player1.id in self.choices and self.player2.id in self.choices

    def result_description(self) -> str:
        c1 = self.choices[self.player1.id]
        c2 = self.choices[self.player2.id]
        lines = [
            f"{self.player1.mention} : {RPS_CHOICES[c1]} **{c1.capitalize()}**",
            f"{self.player2.mention} : {RPS_CHOICES[c2]} **{c2.capitalize()}**",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
        if c1 == c2:
            lines.append("🤝 Égalité !")
        elif RPS_BEATS[c1] == c2:
            lines.append(f"🎉 {self.player1.mention} remporte la partie !")
        else:
            lines.append(f"🎉 {self.player2.mention} remporte la partie !")
        return "\n".join(lines)


class RPSChoiceView(discord.ui.View):
    def __init__(self, match, challenge_view):
        super().__init__(timeout=60)
        self.match = match
        self.challenge_view = challenge_view

    async def _pick(self, interaction: discord.Interaction, choice: str):
        self.match.choices[interaction.user.id] = choice
        await interaction.response.edit_message(
            content=f"✅ Choix enregistré : {RPS_CHOICES[choice]} **{choice.capitalize()}**. En attente de l'adversaire...",
            embed=None, view=None,
        )

        if self.match.both_chosen() and not self.match.finished:
            self.match.finished = True
            for child in self.challenge_view.children:
                child.disabled = True
            embed = discord.Embed(
                title="◈  PIERRE - FEUILLE - CISEAUX - RÉSULTAT  ◈",
                description=self.match.result_description(),
                color=COLOR_SUCCESS,
            )
            embed.set_footer(text="AERON • Mini-jeux", icon_url=AERON_LOGO)
            try:
                await self.match.message.edit(embed=embed, view=self.challenge_view)
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Pierre", emoji="🪨", style=discord.ButtonStyle.secondary)
    async def pierre(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._pick(interaction, "pierre")

    @discord.ui.button(label="Feuille", emoji="📄", style=discord.ButtonStyle.secondary)
    async def feuille(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._pick(interaction, "feuille")

    @discord.ui.button(label="Ciseaux", emoji="✂️", style=discord.ButtonStyle.secondary)
    async def ciseaux(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._pick(interaction, "ciseaux")


class RPSChallengeView(discord.ui.View):
    def __init__(self, match):
        super().__init__(timeout=120)
        self.match = match

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (self.match.player1.id, self.match.player2.id):
            await interaction.response.send_message("❌ Cette partie ne te concerne pas.", ephemeral=True)
            return False
        if interaction.user.id in self.match.choices:
            await interaction.response.send_message("❌ Tu as déjà fait ton choix, en attente de l'adversaire.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Faire son choix", emoji="🎮", style=discord.ButtonStyle.primary)
    async def choose(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="◈  FAIS TON CHOIX  ◈",
            description="Ton choix restera secret jusqu'à ce que l'adversaire ait aussi choisi.",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Mini-jeux", icon_url=AERON_LOGO)
        await interaction.response.send_message(embed=embed, view=RPSChoiceView(self.match, self), ephemeral=True)

# ═════════════════════════════════════════
#  MORPION (1V1) AVEC DÉFI CIBLÉ/LIBRE ET TIMEOUT
# ═════════════════════════════════════════

WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
]


class MorpionMatch:
    def __init__(self, player_x, player_o):
        self.player_x = player_x
        self.player_o = player_o
        self.board = [None] * 9
        self.turn = player_x.id
        self.finished = False
        self.forfeit_by = None  # id du joueur ayant abandonné, sinon None

    def check_result(self):
        for a, b, c in WIN_LINES:
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                return self.board[a]
        if all(self.board):
            return "draw"
        return None

    def current_player(self):
        return self.player_x if self.turn == self.player_x.id else self.player_o

    def symbol_for(self, user_id: int) -> str:
        return "❌" if user_id == self.player_x.id else "⭕"

    def winner(self):
        """Retourne le joueur gagnant, ou None (partie nulle ou en cours)."""
        if self.forfeit_by:
            return self.player_o if self.forfeit_by == self.player_x.id else self.player_x
        result = self.check_result()
        if result and result != "draw":
            return self.player_x if result == "❌" else self.player_o
        return None


def build_morpion_embed(match) -> discord.Embed:
    if not match.finished:
        description = f"Au tour de {match.current_player().mention} ({match.symbol_for(match.current_player().id)})"
        color = COLOR_MAIN
    elif match.forfeit_by:
        loser = match.player_x if match.forfeit_by == match.player_x.id else match.player_o
        winner = match.player_o if match.forfeit_by == match.player_x.id else match.player_x
        description = f"🏳️ {loser.mention} a abandonné. {winner.mention} remporte la partie !"
        color = COLOR_SUCCESS
    else:
        result = match.check_result()
        if result == "draw":
            description = "🤝 Match nul !"
        else:
            winner = match.player_x if result == "❌" else match.player_o
            description = f"🎉 {winner.mention} remporte la partie !"
        color = COLOR_SUCCESS

    embed = discord.Embed(
        title="◈  MORPION  ◈",
        description=(
            f"❌ {match.player_x.mention}  -  ⭕ {match.player_o.mention}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{description}"
        ),
        color=color,
    )
    embed.set_footer(text="AERON • Mini-jeux", icon_url=AERON_LOGO)
    return embed


class MorpionButton(discord.ui.Button):
    def __init__(self, index: int):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=index // 3)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        match = view.match

        if interaction.user.id != match.turn:
            await interaction.response.send_message("❌ Ce n'est pas ton tour.", ephemeral=True)
            return
        if match.board[self.index] is not None:
            await interaction.response.send_message("❌ Cette case est déjà prise.", ephemeral=True)
            return

        symbol = match.symbol_for(interaction.user.id)
        match.board[self.index] = symbol
        self.label = symbol
        self.style = discord.ButtonStyle.danger if symbol == "❌" else discord.ButtonStyle.primary
        self.disabled = True

        result = match.check_result()
        if result:
            match.finished = True
            for child in view.children:
                child.disabled = True
            winner = match.winner()
            if winner:
                award_xp(winner.id, XP_MORPION_WIN)
            await interaction.response.edit_message(embed=build_morpion_embed(match), view=MorpionEndView(match))
            return
        else:
            match.turn = match.player_o.id if interaction.user.id == match.player_x.id else match.player_x.id

        await interaction.response.edit_message(embed=build_morpion_embed(match), view=view)


class MorpionAbandonButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Abandonner", emoji="🏳️", style=discord.ButtonStyle.danger, row=3)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        match = view.match

        if interaction.user.id not in (match.player_x.id, match.player_o.id):
            await interaction.response.send_message("❌ Cette partie ne te concerne pas.", ephemeral=True)
            return
        if match.finished:
            return

        match.finished = True
        match.forfeit_by = interaction.user.id
        for child in view.children:
            child.disabled = True

        winner = match.winner()
        if winner:
            award_xp(winner.id, XP_MORPION_WIN)

        await interaction.response.edit_message(embed=build_morpion_embed(match), view=MorpionEndView(match))


class MorpionView(discord.ui.View):
    def __init__(self, match):
        super().__init__(timeout=300)
        self.match = match
        self.message = None
        for i in range(9):
            self.add_item(MorpionButton(i))
        self.add_item(MorpionAbandonButton())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (self.match.player_x.id, self.match.player_o.id):
            await interaction.response.send_message("❌ Cette partie ne te concerne pas.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if self.match.finished:
            return
        self.match.finished = True
        for child in self.children:
            child.disabled = True
        embed = discord.Embed(
            title="◈  MORPION - EXPIRÉ  ◈",
            description="⏱️ Partie annulée pour cause d'inactivité (5 minutes).",
            color=COLOR_DANGER,
        )
        embed.set_footer(text="AERON • Mini-jeux", icon_url=AERON_LOGO)
        if self.message:
            try:
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass


class MorpionEndView(discord.ui.View):
    def __init__(self, match):
        super().__init__(timeout=120)
        self.match = match

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (self.match.player_x.id, self.match.player_o.id):
            await interaction.response.send_message("❌ Cette partie ne te concerne pas.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Revanche", emoji="🔁", style=discord.ButtonStyle.primary)
    async def revanche(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Le joueur qui commence alterne à chaque revanche
        new_match = MorpionMatch(self.match.player_o, self.match.player_x)
        view = MorpionView(new_match)
        await interaction.response.edit_message(embed=build_morpion_embed(new_match), view=view)
        view.message = await interaction.original_response()


class MorpionAcceptView(discord.ui.View):
    def __init__(self, author, adversaire):
        super().__init__(timeout=60)
        self.author = author
        self.adversaire = adversaire
        self.accepted = False
        self.message = None

    @discord.ui.button(label="Accepter le défi", emoji="✅", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.author.id:
            await interaction.response.send_message("❌ Tu ne peux pas accepter ton propre défi.", ephemeral=True)
            return

        if self.adversaire and interaction.user.id != self.adversaire.id:
            await interaction.response.send_message("❌ Ce défi ne t'est pas destiné !", ephemeral=True)
            return

        self.accepted = True
        self.stop()

        match = MorpionMatch(self.author, interaction.user)
        view = MorpionView(match)
        await interaction.response.edit_message(embed=build_morpion_embed(match), view=view)
        view.message = await interaction.original_response()

    async def on_timeout(self):
        if not self.accepted and self.message:
            for child in self.children:
                child.disabled = True
            embed = discord.Embed(
                title="◈  MORPION - EXPIRÉ  ◈",
                description="Le temps est écoulé (1 minute), le défi a été annulé faute de réponse.",
                color=COLOR_DANGER
            )
            embed.set_footer(text="AERON • Mini-jeux", icon_url=AERON_LOGO)
            try:
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass

# ═════════════════════════════════════════
#  LE PENDU (SAISIE DIRECTE, 0/8 & DESSIN)
# ═════════════════════════════════════════

HANGMAN_WORDS = [
    "REPUBLIQUE", "SENAT", "CHANCELIER", "CLONE", "JEDI", "SITH", "PADAWAN",
    "HOLOCOMM", "BLASTER", "SABRE LASER", "CORUSCANT", "KAMINO", "GEONOSIS",
    "WOOKIEE", "DROIDE", "VAISSEAU", "ESCADRON", "GENERAL", "AMIRAL",
    "NEGOCIATION", "AMBASSADE", "CROISEUR", "HANGAR", "ARMURE", "CASQUE",
    "STORMTROOPER", "HYPERESPACE", "CANTINA", "CONTREBANDIER", "MERCENAIRE",
]

MAX_ERRORS = 11
HANGMAN_ORANGE      = (226, 148, 67)
HANGMAN_ORANGE_DIM  = (140, 92, 42)
HANGMAN_BG          = (13, 13, 15)
HANGMAN_HELMET_FILL = (24, 24, 26)


class HangmanGame:
    def __init__(self, word: str, starter, message):
        self.word = word.upper()
        self.guessed = set()
        self.wrong = set()
        self.starter = starter
        self.message = message
        self.finished = False
        self.close_reason = None  # "stopped" | "timeout" | None
        self.last_activity = time.time()

    def display_word(self) -> str:
        return " ".join(letter if (letter in self.guessed or not letter.isalpha()) else "＿" for letter in self.word)

    def is_won(self) -> bool:
        return all(letter in self.guessed or not letter.isalpha() for letter in self.word)

    def is_lost(self) -> bool:
        return len(self.wrong) >= MAX_ERRORS


def build_hangman_embed(game) -> discord.Embed:
    color = COLOR_MAIN
    result_line = ""
    if game.finished:
        if game.close_reason == "stopped":
            color = COLOR_DANGER
            result_line = f"\n🛑 **Partie arrêtée.** Le mot était **{game.word}**"
        elif game.close_reason == "timeout":
            color = COLOR_DANGER
            result_line = f"\n⏱️ **Partie close pour inactivité (10 min).** Le mot était **{game.word}**"
        elif game.is_won():
            color = COLOR_SUCCESS
            result_line = "\n🎉 **Le mot a été trouvé !**"
        else:
            color = COLOR_DANGER
            result_line = f"\n💀 **Perdu !** Le mot était **{game.word}**"
    elif len(game.wrong) >= 7:
        color = COLOR_DANGER
    elif len(game.wrong) >= 4:
        color = COLOR_WARN

    errors_count = len(game.wrong)
    wrong_letters = ", ".join(sorted(game.wrong)) or "*Aucune*"

    embed = discord.Embed(
        title="◈  LE PENDU  ◈",
        description=(
            f"`{game.display_word()}`\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"❌ Erreurs : `{errors_count}/{MAX_ERRORS}`\n"
            f"Lettres erronées : {wrong_letters}"
            f"{result_line}"
        ),
        color=color,
    )
    embed.set_image(url="attachment://pendu.png")
    embed.set_footer(text="AERON • Mini-jeux", icon_url=AERON_LOGO)
    return embed


def render_hangman_image(errors_count: int) -> io.BytesIO:
    """Dessine la potence en style Aeron (outline orange sur fond noir)."""
    W, H = 420, 300
    img = Image.new("RGB", (W, H), HANGMAN_BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([2, 2, W - 3, H - 3], outline=HANGMAN_ORANGE_DIM, width=2)
    for y in range(20, H - 20, 26):
        draw.line([(20, y), (W - 20, y)], fill=(24, 24, 27), width=1)

    LW = 6
    ground_y = 250
    pole_x = 90
    beam_y = 40
    hook_x = 240

    def draw_helmet(cx, cy):
        r = 24
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=HANGMAN_ORANGE, width=5, fill=HANGMAN_HELMET_FILL)
        draw.line([(cx - 11, cy - 2), (cx + 11, cy - 2)], fill=HANGMAN_ORANGE, width=4)
        draw.line([(cx, cy - 2), (cx, cy + 13)], fill=HANGMAN_ORANGE, width=4)

    stages = [
        lambda: draw.line([(50, ground_y), (250, ground_y)], fill=HANGMAN_ORANGE, width=LW),
        lambda: draw.line([(pole_x, ground_y), (pole_x, beam_y)], fill=HANGMAN_ORANGE, width=LW),
        lambda: draw.line([(pole_x, beam_y), (hook_x, beam_y)], fill=HANGMAN_ORANGE, width=LW),
        lambda: draw.line([(pole_x, beam_y + 32), (pole_x + 32, beam_y)], fill=HANGMAN_ORANGE, width=LW - 2),
        lambda: draw.line([(hook_x, beam_y), (hook_x, beam_y + 32)], fill=HANGMAN_ORANGE, width=LW - 2),
        lambda: draw_helmet(hook_x, beam_y + 56),
        lambda: draw.line([(hook_x, beam_y + 80), (hook_x, beam_y + 138)], fill=HANGMAN_ORANGE, width=LW),
        lambda: draw.line([(hook_x, beam_y + 95), (hook_x - 28, beam_y + 124)], fill=HANGMAN_ORANGE, width=LW - 2),
        lambda: draw.line([(hook_x, beam_y + 95), (hook_x + 28, beam_y + 124)], fill=HANGMAN_ORANGE, width=LW - 2),
        lambda: draw.line([(hook_x, beam_y + 138), (hook_x - 24, beam_y + 176)], fill=HANGMAN_ORANGE, width=LW - 2),
        lambda: draw.line([(hook_x, beam_y + 138), (hook_x + 24, beam_y + 176)], fill=HANGMAN_ORANGE, width=LW - 2),
    ]

    for i in range(min(errors_count, len(stages))):
        stages[i]()

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def build_hangman_payload(game):
    """Retourne (embed, discord.File) prêts à être envoyés/édités ensemble."""
    file = discord.File(fp=render_hangman_image(len(game.wrong)), filename="pendu.png")
    embed = build_hangman_embed(game)
    return embed, file


class HangmanView(discord.ui.View):
    def __init__(self, game):
        super().__init__(timeout=None)
        self.game = game

    @discord.ui.button(label="Arrêter la partie", emoji="🛑", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = self.game
        if game.finished:
            return

        is_starter = interaction.user.id == game.starter.id
        is_mod = isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.manage_messages
        if not (is_starter or is_mod):
            await interaction.response.send_message(
                "❌ Seul l'auteur de la partie ou un modérateur peut l'arrêter.", ephemeral=True
            )
            return

        game.finished = True
        game.close_reason = "stopped"

        cog = interaction.client.get_cog("Games")
        if cog:
            cog.hangman_games.pop(interaction.channel.id, None)

        embed, file = build_hangman_payload(game)
        await interaction.response.edit_message(embed=embed, attachments=[file], view=HangmanEndView(game))


class HangmanEndView(discord.ui.View):
    def __init__(self, game):
        super().__init__(timeout=120)
        self.game = game

    @discord.ui.button(label="Rejouer", emoji="🔁", style=discord.ButtonStyle.primary)
    async def replay(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = interaction.client.get_cog("Games")
        if cog is None:
            return

        existing = cog.hangman_games.get(interaction.channel.id)
        if existing and not existing.finished:
            await interaction.response.send_message(
                "❌ Une partie de pendu est déjà en cours dans ce salon.", ephemeral=True
            )
            return

        word = random.choice(HANGMAN_WORDS)
        new_game = HangmanGame(word, interaction.user, None)
        cog.hangman_games[interaction.channel.id] = new_game

        embed, file = build_hangman_payload(new_game)
        await interaction.response.edit_message(embed=embed, attachments=[file], view=HangmanView(new_game))
        new_game.message = await interaction.original_response()

# ═════════════════════════════════════════
#  COG PRINCIPAL
# ═════════════════════════════════════════

class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hangman_games = {}
        self.check_hangman_inactivity.start()

    def cog_unload(self):
        self.check_hangman_inactivity.cancel()

    @tasks.loop(minutes=2)
    async def check_hangman_inactivity(self):
        now = time.time()
        stale_ids = [
            cid for cid, g in self.hangman_games.items()
            if not g.finished and now - g.last_activity > HANGMAN_INACTIVITY_LIMIT
        ]
        for channel_id in stale_ids:
            game = self.hangman_games.pop(channel_id, None)
            if not game:
                continue
            game.finished = True
            game.close_reason = "timeout"
            try:
                embed, file = build_hangman_payload(game)
                await game.message.edit(embed=embed, attachments=[file], view=HangmanEndView(game))
            except discord.HTTPException:
                pass

    @check_hangman_inactivity.before_loop
    async def before_check_hangman_inactivity(self):
        await self.bot.wait_until_ready()

    async def _end_hangman(self, game, channel_id: int, won: bool, finisher: discord.Member):
        game.finished = True
        self.hangman_games.pop(channel_id, None)
        if won:
            award_xp(finisher.id, XP_PENDU_WIN)
        try:
            embed, file = build_hangman_payload(game)
            await game.message.edit(embed=embed, attachments=[file], view=HangmanEndView(game))
        except discord.HTTPException:
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        game = self.hangman_games.get(message.channel.id)
        if not game or game.finished:
            return

        content = message.content.strip().upper()

        if len(content) == 1 and content.isalpha():
            try:
                await message.delete()
            except discord.HTTPException:
                pass

            if content in game.guessed or content in game.wrong:
                return

            if content in game.word:
                game.guessed.add(content)
            else:
                game.wrong.add(content)
            game.last_activity = time.time()

            if game.is_won():
                await self._end_hangman(game, message.channel.id, True, message.author)
                return
            if game.is_lost():
                await self._end_hangman(game, message.channel.id, False, message.author)
                return

            try:
                embed, file = build_hangman_payload(game)
                await game.message.edit(embed=embed, attachments=[file])
            except discord.HTTPException:
                pass

        elif len(content) > 1 and content.isalpha():
            try:
                await message.delete()
            except discord.HTTPException:
                pass

            if content == game.word:
                game.guessed.update(set(game.word))
            else:
                game.wrong.add(content[:1])
            game.last_activity = time.time()

            if game.is_won():
                await self._end_hangman(game, message.channel.id, True, message.author)
                return
            if game.is_lost():
                await self._end_hangman(game, message.channel.id, False, message.author)
                return

            try:
                embed, file = build_hangman_payload(game)
                await game.message.edit(embed=embed, attachments=[file])
            except discord.HTTPException:
                pass

    # ── PIERRE-FEUILLE-CISEAUX ──

    @app_commands.command(name="rps", description="Défier un joueur à Pierre-Feuille-Ciseaux")
    @app_commands.describe(adversaire="Le joueur à défier")
    async def rps(self, interaction: discord.Interaction, adversaire: discord.Member):
        if adversaire.bot:
            await interaction.response.send_message("❌ Tu ne peux pas défier un bot.", ephemeral=True)
            return
        if adversaire.id == interaction.user.id:
            await interaction.response.send_message("❌ Tu ne peux pas te défier toi-même.", ephemeral=True)
            return

        match = RPSMatch(interaction.user, adversaire)
        embed = discord.Embed(
            title="◈  PIERRE - FEUILLE - CISEAUX  ◈",
            description=(
                f"{interaction.user.mention} défie {adversaire.mention} !\n"
                "Cliquez sur le bouton ci-dessous pour faire votre choix en secret."
            ),
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Mini-jeux", icon_url=AERON_LOGO)
        view = RPSChallengeView(match)
        await interaction.response.send_message(embed=embed, view=view)
        match.message = await interaction.original_response()

    # ── MORPION ──

    @app_commands.command(name="morpion", description="Défier un joueur au morpion (Laisser vide pour un défi libre)")
    @app_commands.describe(adversaire="Le joueur à défier (optionnel)")
    async def morpion(self, interaction: discord.Interaction, adversaire: discord.Member = None):
        if adversaire:
            if adversaire.bot:
                await interaction.response.send_message("❌ Tu ne peux pas défier un bot.", ephemeral=True)
                return
            if adversaire.id == interaction.user.id:
                await interaction.response.send_message("❌ Tu ne peux pas te défier toi-même.", ephemeral=True)
                return

        view = MorpionAcceptView(interaction.user, adversaire)

        desc = f"{interaction.user.mention} lance un défi de Morpion **libre** !\nLe premier à cliquer sur le bouton ci-dessous affrontera l'auteur."
        if adversaire:
            desc = f"{interaction.user.mention} défie {adversaire.mention} au Morpion !\n{adversaire.mention} a 1 minute pour accepter."

        embed = discord.Embed(
            title="◈  DÉFI MORPION  ◈",
            description=desc,
            color=COLOR_MAIN
        )
        embed.set_footer(text="AERON • Mini-jeux", icon_url=AERON_LOGO)

        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    # ── PENDU ──

    @app_commands.command(name="pendu", description="Démarrer une partie de pendu dans ce salon")
    async def pendu(self, interaction: discord.Interaction):
        existing = self.hangman_games.get(interaction.channel.id)
        if existing and not existing.finished:
            await interaction.response.send_message("❌ Une partie de pendu est déjà en cours dans ce salon.", ephemeral=True)
            return

        word = random.choice(HANGMAN_WORDS)

        embed = discord.Embed(title="Chargement...", color=COLOR_MAIN)
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()

        game = HangmanGame(word, interaction.user, msg)
        self.hangman_games[interaction.channel.id] = game

        embed, file = build_hangman_payload(game)
        await msg.edit(embed=embed, attachments=[file], view=HangmanView(game))

    # ── PILE OU FACE ──

    @app_commands.command(name="pile-ou-face", description="Lancer une pièce")
    async def pile_ou_face(self, interaction: discord.Interaction):
        result = random.choice(["Pile", "Face"])
        embed = discord.Embed(
            title="◈  PILE OU FACE  ◈",
            description=f"🪙 La pièce tombe sur... **{result}** !",
            color=COLOR_MAIN,
        )
        embed.set_footer(text="AERON • Mini-jeux", icon_url=AERON_LOGO)
        await interaction.response.send_message(embed=embed)

    # ── ROLL RP ──

    @app_commands.command(name="roll", description="Lancer un roll pour une action RP")
    @app_commands.describe(
        action="Description de l'action tentée",
        difficulte="Valeur maximale du roll (défaut 100)",
    )
    async def roll(self, interaction: discord.Interaction, action: str, difficulte: app_commands.Range[int, 2, 1000] = 100):
        result = random.randint(1, difficulte)
        ratio = result / difficulte

        if ratio >= 0.9:
            verdict = "🌟 **Réussite critique !**"
            color = COLOR_SUCCESS
        elif ratio >= 0.5:
            verdict = "✅ **Réussite**"
            color = COLOR_SUCCESS
        elif ratio >= 0.2:
            verdict = "⚠️ **Réussite partielle**"
            color = COLOR_WARN
        else:
            verdict = "❌ **Échec**"
            color = COLOR_DANGER

        embed = discord.Embed(
            title="◈  ROLL RP  ◈",
            description=(
                f"{interaction.user.mention} tente : *{action}*\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🎲 Résultat : **{result}/{difficulte}**\n"
                f"{verdict}"
            ),
            color=color,
        )
        embed.set_footer(text="AERON • Roll RP", icon_url=AERON_LOGO)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Games(bot))