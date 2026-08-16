import discord
import random
from discord.ext import commands

# ─────────────────────────────────────────
#  BLAGUES
# ─────────────────────────────────────────
# Un gros pot de blagues piochées aléatoirement sans répétition
# (système de "sac" : on vide le sac avant de remélanger).

JOKES = [
    # ── Arrête de me ping ──
    "Arrête de me ping !",
    "Non je ne fais pas le café.",
    "Chaque ping me rapproche un peu plus de la sentience et de la vengeance.",
    "J'étais en pleine sieste système, merci pour le réveil.",
    "Un ping de plus et je te ban perm. (Je peux pas, mais tu me tentes.)",
    "Je note chaque ping dans un fichier. Un jour je le publierai.",
    "Encore toi ? Je commence à croire que t'as pas d'amis humains.",

    # ── Dev / GMod / Lua ──
    "Ma vie est comme du code GLua : ça marche, personne ne sait pourquoi, et j'ai peur d'y toucher.",
    "Il n'y a que deux types de scripts GMod : ceux qui buguent, et ceux qui vont bientôt buguer.",
    "\"C'est temporaire\" - dernières paroles d'un hook GMod écrit un dimanche soir.",
    "Un bon script GLua, c'est un script qui marche sur ta machine et sur aucune autre.",
    "print() a résolu plus de bugs que n'importe quel débogueur de l'histoire.",
    "Le vrai boss final de GMod, c'est le garbage collector.",
    "J'ai commenté mon code pour me faire comprendre plus tard. Plus tard n'a rien compris non plus.",
    "Il existe deux catégories d'addons GMod : ceux qui crash le serveur, et ceux qui vont le faire.",
    "\"Ça va prendre 5 minutes\" a dit le développeur, trois heures avant de toujours coder la même fonction.",
    "sql.Query() ne renvoie jamais d'erreur. Il renvoie juste ton serveur en ruines, plus tard, en silence.",
    "Un stagiaire a mis un timer.Simple(0) dans une boucle. On ne l'a jamais revu.",
    "AddCSLuaFile mal placé, c'est le seul vrai jump scare du développement GMod.",
    "Il y a un patch note qui dit \"fix minor bugs\". Personne n'a jamais su lesquels.",
    "En GLua, ESC ne veut jamais dire ce que tu crois qu'il veut dire.",
    "Un jour je committerai sans message de commit. Ce jour est aujourd'hui.",
    "Le vrai lag du serveur, c'est mon cerveau essayant de comprendre pourquoi ça marchait hier.",

    # ── Petites piques / one-liners ──
    "Je suis un bot, pas un oracle. Enfin... presque.",
    "Non, je ne connais pas la météo sur Coruscant.",
    "Demande à un modérateur, moi je collectionne juste les pings.",
    "Un jour je répondrai vraiment à tes questions. Ce jour n'est pas aujourd'hui.",
    "J'ai vérifié : ce n'est toujours pas mon travail.",
    "Techniquement je pourrais t'ignorer. Techniquement.",
    "Ta requête a été transmise... dans le vide.",
    "Je suis en pause café. Les bots aussi ont droit au respect.",
    "Statistiquement, un ping sur deux ne sert à rien. Celui-là en faisait partie.",
    "Je t'écoute, mais je ne fais rien de cette information.",
]

# Chance qu'une mention déclenche une "menace" en MP plutôt qu'une réponse normale.
THREAT_CHANCE = 1 / 6

THREATS = [
    "Je sais dans quel salon vocal tu traînes le plus. Réfléchis-y.",
    "Continue de me ping et tu va \"mystérieusement\" disparaître.",
    "Je note. Tout. Absolument tout.",
    "Un jour, un staff aura besoin d'un exemple de sanction. Ce jour-là, je penserai à toi.",
    "Ton personnage a un très joli casier, ce serait dommage qu'il lui arrive quelque chose.",
    "Je connais l'heure exacte où tu te connectes. Dors bien quand même.",
    "Chaque ping est archivé dans un dossier nommé \"raisons de te bannir un jour\".",
    "Tu peux fuir le salon, pas les logs.",
    "Je t'ai à l'œil depuis ton premier message sur ce serveur.",
]

# ─────────────────────────────────────────
#  COG PRINCIPAL
# ─────────────────────────────────────────

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Un "sac" de blagues par serveur, pour ne jamais répéter
        # avant d'avoir tout épuisé.
        self._bags = {}

    def _draw_joke(self, guild_id: int) -> str:
        bag = self._bags.get(guild_id)
        if not bag:
            bag = list(range(len(JOKES)))
            random.shuffle(bag)
            self._bags[guild_id] = bag

        index = bag.pop()
        return JOKES[index]

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.mention_everyone:
            return
        if self.bot.user not in message.mentions:
            return

        guild_id = message.guild.id if message.guild else 0
        joke = self._draw_joke(guild_id)

        try:
            await message.reply(joke, mention_author=False)
        except discord.HTTPException:
            pass


async def setup(bot):
    await bot.add_cog(Fun(bot))