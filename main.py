import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load token dari .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

FILE_PESERTA = "peserta_turnamen.txt"


@bot.event
async def on_ready():
    print(f'✅ Bot aktif sebagai {bot.user}')


@bot.command()
async def daftar(ctx):
    user_id = str(ctx.author.id)
    username = str(ctx.author)

    if not os.path.exists(FILE_PESERTA):
        open(FILE_PESERTA, "w").close()

    with open(FILE_PESERTA, "r") as f:
        daftar_id = [line.strip().split(" ")[-1] for line in f.readlines()]

    if user_id in daftar_id:
        await ctx.send(
            f"⚠️ {ctx.author.mention} kamu *sudah terdaftar* di turnamen.")
    else:
        with open(FILE_PESERTA, "a") as f:
            f.write(f"{username} {user_id}\n")
        await ctx.send(
            f"✅ {ctx.author.mention} pendaftaran *berhasil*! Semangat bertarung!"
        )


@bot.command()
async def peserta(ctx):
    if not os.path.exists(FILE_PESERTA):
        await ctx.send("❌ Belum ada peserta yang mendaftar.")
        return

    with open(FILE_PESERTA, "r") as f:
        lines = f.readlines()

    if not lines:
        await ctx.send("❌ Belum ada peserta yang mendaftar.")
    else:
        daftar = [
            f"{i+1}. {line.split(' ')[0]}" for i, line in enumerate(lines)
        ]
        daftar_str = "\n".join(daftar)
        await ctx.send(f"📋 **DAFTAR PESERTA TURNAMEN:**\n{daftar_str}")


from flask import Flask
from threading import Thread

app = Flask('')


@app.route('/')
def home():
    return "Furina bot aktif!"


def run():
    app.run(host='0.0.0.0', port=8080)


Thread(target=run).start()

# Jalankan bot
bot.run(TOKEN)
