import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    guild = discord.Object(id=1527995014938890322)
    bot.tree.copy_global_to(guild=guild)
    await bot.tree.sync(guild=guild)

    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.CustomActivity(
            name="Veille opérationnelle | Aeron"
        )
    )

    print(f"✅ Connecté en tant que {bot.user}")
    print(f"📡 Nombre de serveurs : {len(bot.guilds)}")
    print("--- Liste des serveurs ---")
    for g in bot.guilds:
        print(f"• {g.name} (ID: {g.id})")
    print("--------------------------")

async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            await bot.load_extension(f"cogs.{filename[:-3]}")
            print(f"🔧 Cog chargé : {filename}")

async def main():
    async with bot:
        await load_cogs()
        await bot.start(os.getenv("DISCORD_TOKEN"))

asyncio.run(main())