import discord
import json
import os
import random
import string
import io
import asyncio
from datetime import datetime
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ─────────────────────────────────────────
#  DA AERON
# ─────────────────────────────────────────

AERON_LOGO    = "https://media.discordapp.net/attachments/1081628825798058079/1517942955254747227/logo.png?ex=6a381e0a&is=6a36cc8a&hm=355f5b01ca46bb58ffce952cfa88e82fdcc39d9205525331a623c3a173958aca&=&format=webp&quality=lossless"
COLOR_MAIN    = 0x012248
COLOR_SUCCESS = 0x1A6B3A
COLOR_DANGER  = 0x8B1A1A
COLOR_WARN    = 0xB8860B

CONFIG_FILE = "config.json"

# ─────────────────────────────────────────
#  STOCKAGE DES CAPTCHAS EN COURS
#  { member_id: { "code": "X7K2P", "attempts": 0 } }
# ─────────────────────────────────────────

active_captchas = {}

# ─────────────────────────────────────────
#  UTILS
# ─────────────────────────────────────────

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def generate_captcha_code(length=6) -> str:
    chars = string.ascii_uppercase + string.digits
    # Éviter les caractères ambigus
    chars = chars.replace("0", "").replace("O", "").replace("I", "").replace("1", "")
    return "".join(random.choices(chars, k=length))

def generate_captcha_image(code: str) -> io.BytesIO:
    width, height = 280, 90
    img = Image.new("RGB", (width, height), color=(1, 18, 72))  # Bleu AERON

    draw = ImageDraw.Draw(img)

    # Bruit de fond — lignes aléatoires
    for _ in range(8):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line([(x1, y1), (x2, y2)], fill=(random.randint(50, 150), random.randint(50, 150), random.randint(100, 200)), width=1)

    # Bruit de fond — points
    for _ in range(200):
        x, y = random.randint(0, width), random.randint(0, height)
        draw.point((x, y), fill=(random.randint(100, 200), random.randint(100, 200), random.randint(150, 255)))

    # Texte — chaque lettre avec position et rotation légèrement aléatoires
    try:
        font = ImageFont.truetype("arial.ttf", 42)
    except:
        font = ImageFont.load_default()

    x_offset = 20
    for char in code:
        y_offset = random.randint(10, 30)
        color = (
            random.randint(180, 255),
            random.randint(180, 255),
            random.randint(200, 255),
        )
        draw.text((x_offset, y_offset), char, font=font, fill=color)
        x_offset += random.randint(38, 45)

    # Flou léger pour rendre moins lisible par les bots
    img = img.filter(ImageFilter.GaussianBlur(radius=0.8))

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

async def send_captcha(channel: discord.TextChannel, member: discord.Member, bot) -> discord.Message:
    code = generate_captcha_code()
    active_captchas[member.id] = {"code": code, "attempts": 0, "message_id": None}

    image_buffer = generate_captcha_image(code)
    file         = discord.File(fp=image_buffer, filename="captcha.png")

    embed = discord.Embed(
        title="◈  VÉRIFICATION REQUISE  ◈",
        description=(
            f"{member.mention} - Bienvenue sur **Aeron**.\n\n"
            "Pour accéder au serveur, tape le code affiché sur l'image ci-dessous.\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ **3 tentatives** avant expulsion.\n"
            "⚠️ Le code est **insensible à la casse**.\n"
            "⏱️ **2 minutes** pour répondre."
        ),
        color=COLOR_MAIN,
    )
    embed.set_image(url="attachment://captcha.png")
    embed.set_footer(text="Aeron • Système de vérification", icon_url=AERON_LOGO)

    msg = await channel.send(embed=embed, file=file)
    active_captchas[member.id]["message_id"] = msg.id

    # Timer 2 minutes
    asyncio.ensure_future(captcha_timeout(member, channel, msg, bot))

    return msg

async def captcha_timeout(member: discord.Member, channel: discord.TextChannel, msg: discord.Message, bot):
    await asyncio.sleep(120)

    if member.id not in active_captchas:
        return  # Déjà vérifié

    del active_captchas[member.id]

    # Supprimer le message captcha
    try:
        await msg.delete()
    except:
        pass

    # Kick
    try:
        dm_embed = discord.Embed(
            title="◈  DÉLAI EXPIRÉ  ◈",
            description=(
                f"Tu as été expulsé du serveur **{member.guild.name}**.\n"
                "Tu n'as pas complété la vérification dans les 2 minutes imparties.\n"
                "Tu peux rejoindre à nouveau et réessayer."
            ),
            color=COLOR_DANGER,
        )
        dm_embed.set_footer(text="AERON • Système de vérification", icon_url=AERON_LOGO)
        await member.send(embed=dm_embed)
    except:
        pass

    try:
        await member.kick(reason="Délai de vérification expiré")
    except:
        pass

    # Log
    log_embed = discord.Embed(
        title="⏱️ Délai expiré - Kick",
        color=COLOR_DANGER,
    )
    log_embed.add_field(name="◈ Membre", value=f"{member} (`{member.id}`)", inline=True)
    log_embed.add_field(name="◈ Raison", value="2 minutes écoulées sans réponse", inline=True)
    log_embed.set_footer(
        text=f"AERON • {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        icon_url=AERON_LOGO
    )
    await send_captcha_log(member.guild, log_embed)

async def send_captcha_log(guild: discord.Guild, embed: discord.Embed):
    config     = load_config()
    channel_id = config.get("captcha", {}).get("logs_channel_id")
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        await channel.send(embed=embed)

# ─────────────────────────────────────────
#  COG
# ─────────────────────────────────────────

class Captcha(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config  = load_config()
        captcha = config.get("captcha", {})

        if not captcha.get("enabled"):
            return

        unverified_role_id = captcha.get("unverified_role_id")
        channel_id         = captcha.get("verification_channel_id")

        if not unverified_role_id or not channel_id:
            return

        unverified_role = member.guild.get_role(unverified_role_id)
        if unverified_role:
            await member.add_roles(unverified_role)

        channel = member.guild.get_channel(channel_id)
        if channel:
            await send_captcha(channel, member, self.bot)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        config  = load_config()
        captcha = config.get("captcha", {})

        if not captcha.get("enabled"):
            return

        channel_id = captcha.get("verification_channel_id")
        if not channel_id or message.channel.id != channel_id:
            return

        member = message.author

        # Supprimer le message du membre dans tous les cas
        try:
            await message.delete()
        except:
            pass

        if member.id not in active_captchas:
            return

        captcha_data = active_captchas[member.id]
        user_input   = message.content.strip().upper()

        # Bonne réponse
        if user_input == captcha_data["code"]:
            # Supprimer le message captcha
            try:
                captcha_msg = await message.channel.fetch_message(captcha_data["message_id"])
                await captcha_msg.delete()
            except:
                pass

            del active_captchas[member.id]

            verified_role_id   = captcha.get("verified_role_id")
            unverified_role_id = captcha.get("unverified_role_id")

            verified_role   = message.guild.get_role(verified_role_id)
            unverified_role = message.guild.get_role(unverified_role_id)

            if verified_role:
                await member.add_roles(verified_role)
            if unverified_role:
                await member.remove_roles(unverified_role)

            embed = discord.Embed(
                title="◈  VÉRIFICATION RÉUSSIE  ◈",
                description=(
                    f"{member.mention} — Vérification réussie !\n"
                    "Tu as maintenant accès au serveur d'**Aeron**.\n\n"
                    "*- Protocole A.E.R.O.N*"
                ),
                color=COLOR_SUCCESS,
            )
            embed.set_footer(text="AERON • Système de vérification", icon_url=AERON_LOGO)
            msg = await message.channel.send(embed=embed)

            await asyncio.sleep(5)
            await msg.delete()

            # Log
            log_embed = discord.Embed(title="✅ Vérification réussie", color=COLOR_SUCCESS)
            log_embed.add_field(name="◈ Membre",     value=member.mention,                      inline=True)
            log_embed.add_field(name="◈ Tentatives", value=f"`{captcha_data['attempts'] + 1}`", inline=True)
            log_embed.set_footer(
                text=f"AERON • {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                icon_url=AERON_LOGO
            )
            await send_captcha_log(message.guild, log_embed)

        else:
            # Mauvaise réponse
            captcha_data["attempts"] += 1

            if captcha_data["attempts"] >= 3:
                # Supprimer le message captcha
                try:
                    captcha_msg = await message.channel.fetch_message(captcha_data["message_id"])
                    await captcha_msg.delete()
                except:
                    pass

                del active_captchas[member.id]

                try:
                    dm_embed = discord.Embed(
                        title="◈  VÉRIFICATION ÉCHOUÉE  ◈",
                        description=(
                            f"Tu as été expulsé du serveur **{message.guild.name}**.\n"
                            "Tu as échoué 3 fois la vérification captcha.\n"
                            "Tu peux rejoindre à nouveau et réessayer."
                        ),
                        color=COLOR_DANGER,
                    )
                    dm_embed.set_footer(text="AERON • Système de vérification", icon_url=AERON_LOGO)
                    await member.send(embed=dm_embed)
                except:
                    pass

                await member.kick(reason="Échec du captcha - 3 tentatives")

                log_embed = discord.Embed(title="❌ Vérification échouée - Kick", color=COLOR_DANGER)
                log_embed.add_field(name="◈ Membre", value=f"{member} (`{member.id}`)", inline=True)
                log_embed.add_field(name="◈ Raison", value="3 tentatives échouées",     inline=True)
                log_embed.set_footer(
                    text=f"AERON • {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                    icon_url=AERON_LOGO
                )
                await send_captcha_log(message.guild, log_embed)

            else:
                # Supprimer l'ancien captcha
                try:
                    captcha_msg = await message.channel.fetch_message(captcha_data["message_id"])
                    await captcha_msg.delete()
                except:
                    pass

                restantes = 3 - captcha_data["attempts"]
                embed = discord.Embed(
                    title="◈  CODE INCORRECT  ◈",
                    description=(
                        f"{member.mention} — Code incorrect !\n"
                        f"Il te reste **{restantes} tentative{'s' if restantes > 1 else ''}**.\n"
                        "Un nouveau captcha a été généré."
                    ),
                    color=COLOR_WARN,
                )
                embed.set_footer(text="AERON • Système de vérification", icon_url=AERON_LOGO)
                msg = await message.channel.send(embed=embed)

                await asyncio.sleep(3)
                await msg.delete()

                # Nouveau captcha
                await send_captcha(message.channel, member, self.bot)


async def setup(bot):
    await bot.add_cog(Captcha(bot))