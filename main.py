import discord
from discord.ext import commands, tasks
import os
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta

TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = int(os.environ["CHANNEL_ID"])

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

FILE_PESERTA = "peserta_turnamen.txt"

sapaan_harian = {
    "Monday": "@here Selamat hari Senin! Awali minggu ini dengan semangat penuh energi 💪🔥",
    "Tuesday": "@here Selamat hari Selasa! Tetap fokus dan semangat dalam semua aktivitasmu hari ini 💯🚀",
    "Wednesday": "@here Selamat hari Rabu! Jangan menyerah di tengah minggu, kamu luar biasa! 🌟✨",
    "Thursday": "@here Selamat hari Kamis! Langkahkan kaki dengan optimis, sukses menanti di depan 🏃‍♂️💼",
    "Friday": "@here Selamat hari Jumat! Akhiri minggu ini dengan semangat terbaikmu! 🎉💥",
    "Saturday": "@here Selamat hari Sabtu! Nikmati waktumu, recharge energi dan tetap produktif 😎🌈",
    "Sunday": "@here Selamat hari Minggu! Waktunya istirahat sejenak dan siapkan diri untuk minggu baru 🌿🛌",
}


@bot.event
async def on_ready():
    print(f'✅ Bot aktif sebagai {bot.user}')
    sapa_harian.start()


@tasks.loop(minutes=1)
async def sapa_harian():
    now = datetime.utcnow() + timedelta(hours=7)
    if now.hour == 7 and now.minute == 0:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            hari = now.strftime("%A")
            pesan = sapaan_harian.get(hari, "@here Selamat pagi semuanya!")
            await channel.send(pesan)


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


@bot.command()
async def hapus(ctx):
    user_id = str(ctx.author.id)
    if not os.path.exists(FILE_PESERTA):
        await ctx.send("❌ Tidak ada data peserta.")
        return

    with open(FILE_PESERTA, "r") as f:
        lines = f.readlines()

    with open(FILE_PESERTA, "w") as f:
        found = False
        for line in lines:
            if user_id not in line:
                f.write(line)
            else:
                found = True

    if found:
        await ctx.send(f"✅ {ctx.author.mention} kamu berhasil *dihapus* dari daftar.")
    else:
        await ctx.send(f"⚠️ {ctx.author.mention} kamu *tidak ditemukan* dalam daftar.")


@bot.command()
async def hapussema(ctx):
    if os.path.exists(FILE_PESERTA):
        open(FILE_PESERTA, "w").close()
        await ctx.send("🗑 Semua data peserta telah dihapus.")
    else:
        await ctx.send("❌ File peserta tidak ditemukan.")


@bot.command()
async def tes(ctx):
    now = datetime.utcnow() + timedelta(hours=7)
    hari = now.strftime("%A")
    pesan = sapaan_harian.get(hari, "@here Selamat pagi semuanya!")
    await ctx.send(f"(Tes) {pesan}")


@bot.command(name="help")
async def custom_help(ctx):
    help_text = (
        "**📘 Command Furina Bot:**\n"
        "`!daftar` – Daftar sebagai peserta turnamen.\n"
        "`!peserta` – Lihat daftar peserta.\n"
        "`!hapus` – Hapus dirimu dari daftar peserta.\n"
        "`!hapussema` – Hapus semua peserta (admin only).\n"
        "`!tes` – Tes sapaan harian sekarang.\n"
        "`!help` – Tampilkan daftar perintah ini.\n"
    )
    await ctx.send(help_text)


# Webserver agar Railway tetap hidup
app = Flask('')


@app.route('/')
def home():
    return "Furina bot aktif!"


def run():
    app.run(host='0.0.0.0', port=8080)


Thread(target=run).start()

bot.run(TOKEN)
