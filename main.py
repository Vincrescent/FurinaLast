import discord
from discord.ext import commands, tasks
import os
from datetime import datetime
from flask import Flask
from threading import Thread

# === Konfigurasi ===
TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
FILE_PESERTA = "peserta_turnamen.txt"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# === Sapaan Harian ===
sapaan_harian = {
    "Monday": "Selamat hari Senin! Semangat awal minggu! 💪",
    "Tuesday": "Selamat hari Selasa! Jalani hari ini dengan semangat! ☀️",
    "Wednesday": "Selamat hari Rabu! Semoga harimu menyenangkan! 😊",
    "Thursday": "Selamat hari Kamis! Akhir pekan sudah dekat! ✨",
    "Friday": "Selamat hari Jumat! Semangat menjelang weekend! 🎉",
    "Saturday": "Selamat hari Sabtu! Nikmati waktu luangmu! 😎",
    "Sunday": "Selamat hari Minggu! Saatnya recharge energi! 🔋",
}

@bot.event
async def on_ready():
    print(f'✅ Bot aktif sebagai {bot.user}')
    sapa_harian.start()

@tasks.loop(minutes=1)
async def sapa_harian():
    now = datetime.now()
    if now.hour == 8 and now.minute == 0:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            hari = now.strftime("%A")
            pesan = sapaan_harian.get(hari, "Selamat pagi semuanya!")
            await channel.send(pesan)

# === Command daftar ===
@bot.command()
async def daftar(ctx):
    user_id = str(ctx.author.id)
    username = str(ctx.author)

    if not os.path.exists(FILE_PESERTA):
        open(FILE_PESERTA, "w").close()

    with open(FILE_PESERTA, "r") as f:
        daftar_id = [line.strip().split(" ")[-1] for line in f.readlines()]

    if user_id in daftar_id:
        await ctx.send(f"⚠️ {ctx.author.mention} kamu *sudah terdaftar* di turnamen.")
    else:
        with open(FILE_PESERTA, "a") as f:
            f.write(f"{username} {user_id}\n")
        await ctx.send(f"✅ {ctx.author.mention} pendaftaran *berhasil*! Semangat bertarung!")

# === Command peserta ===
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
        daftar = [f"{i+1}. {line.split(' ')[0]}" for i, line in enumerate(lines)]
        daftar_str = "\n".join(daftar)
        await ctx.send(f"📋 **DAFTAR PESERTA TURNAMEN:**\n{daftar_str}")

# === Command hapus peserta ===
@bot.command()
async def hapus(ctx):
    user_id = str(ctx.author.id)

    if not os.path.exists(FILE_PESERTA):
        await ctx.send("❌ Belum ada data peserta.")
        return

    with open(FILE_PESERTA, "r") as f:
        lines = f.readlines()

    baru = [line for line in lines if not line.endswith(f"{user_id}\n")]

    if len(baru) == len(lines):
        await ctx.send(f"⚠️ {ctx.author.mention} kamu belum terdaftar.")
    else:
        with open(FILE_PESERTA, "w") as f:
            f.writelines(baru)
        await ctx.send(f"🗑️ {ctx.author.mention} kamu telah dihapus dari daftar peserta.")

# === Command hapus semua peserta (admin only) ===
@bot.command()
@commands.has_permissions(administrator=True)
async def hapussemua(ctx):
    if os.path.exists(FILE_PESERTA):
        os.remove(FILE_PESERTA)
        await ctx.send("🧹 Semua data peserta berhasil dihapus.")
    else:
        await ctx.send("⚠️ Tidak ada data untuk dihapus.")

# === Webserver Keep Alive (Railway / Replit) ===
app = Flask('')

@app.route('/')
def home():
    return "Furina bot aktif!"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# === Jalankan Bot ===
bot.run(TOKEN)
