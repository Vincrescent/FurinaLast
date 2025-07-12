import discord
from discord.ext import commands, tasks
from flask import Flask
from threading import Thread
import os
import random
from datetime import datetime
import pytz
import re

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='f.', intents=intents)

FILE_PESERTA = "peserta_turnamen.txt"

# === Respon Interaktif Tanpa Prefix ===
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()
    mentioned = bot.user in message.mentions or "furina" in content

    if mentioned:
        if re.search(r"\bhalo\b", content):
            responses = [
                "🎀 Hmph, siapa yang memanggil Furina? Baiklah, halo juga~",
                "💧 Furina menyapamu dengan gaya Fontaine yang anggun!",
                "🎭 Halo! Panggung ini terlalu sepi tanpamu!",
                "😤 Jangan ganggu aku... eh?! Kamu cuma mau bilang halo? Ugh... baiklah, halo!",
            ]
            await message.channel.send(random.choice(responses))
            return

        if re.search(r"\b(hug|peluk)\b", content):
            responses = [
                f"😳 E-eh?! Pelukan? B-baiklah... hanya kali ini, ya {message.author.mention}...",
                "💙 Kau beruntung Furina sedang baik hati! Ini pelukan spesial dari Archon Hydro~",
                "🌊 Pelukan? Jangan salah sangka! Aku hanya sedang dalam suasana hati yang baik!",
                "🎭 Furina memelukmu seperti layaknya aktris utama memeluk penggemarnya~",
            ]
            await message.channel.send(random.choice(responses))
            return

        if re.search(r"\b(puji|puja)\b", content):
            responses = [
                "🌟 Hah! Tentu saja aku memujimu! Tapi jangan lupakan siapa yang paling bersinar di sini, yaitu aku!",
                f"✨ {message.author.mention}, kau tampil cukup baik hari ini. Jangan mengecewakan panggung Fontaine!",
                "🎀 Baiklah... kau layak mendapatkan pujian. Tapi itu tidak membuatmu lebih hebat dariku!",
                "💙 Bahkan Furina pun mengakui keberanianmu. Hebat, bintang kecil!",
            ]
            await message.channel.send(random.choice(responses))
            return

    await bot.process_commands(message)

# === Command ===
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
        await ctx.send(f"📋 **DAFTAR PESERTA TURNAMEN:**\n" + "\n".join(daftar))

@bot.command()
async def hapus(ctx):
    if os.path.exists(FILE_PESERTA):
        os.remove(FILE_PESERTA)
        await ctx.send("🗑️ Semua data peserta telah dihapus.")
    else:
        await ctx.send("📂 Tidak ada data untuk dihapus.")

@bot.command()
async def tes(ctx):
    await ctx.send(random.choice(pesan_sapa_pagi()))

@bot.command()
async def help(ctx):
    help_text = (
        "**📖 COMMAND FURINA**\n"
        "`f.daftar` → Daftarkan dirimu ke turnamen.\n"
        "`f.peserta` → Lihat daftar peserta yang sudah mendaftar.\n"
        "`f.hapus` → Menghapus semua data peserta.\n"
        "`f.tes` → Tes sapaan Furina.\n\n"
        "**✨ Tanpa Prefix:**\n"
        "Ketik saja `halo @Furina`, `peluk aku Furina`, atau `puji aku Furina`!"
    )
    await ctx.send(help_text)

# === Sapa Pagi & Malam ===
def pesan_sapa_pagi():
    return [
        "🎭 *Selamat pagi semuanya!* Semoga hari ini penuh kejutan indah dan energi dramatis ala Fontaine! @here",
        "🌊 Furina datang membawa semangat! Mari kita mulai hari ini dengan aksi luar biasa! @here",
        "✨ Wahai para bintang panggung! Hari ini adalah kesempatan untuk bersinar lagi~ @here",
        "💙 Ayo bangkit dari tidur! Hidup ini adalah pertunjukan yang harus kau menangkan! @here"
    ]

def pesan_sapa_malam():
    return [
        "🌙 Malam telah tiba! Jangan lupa istirahat, para penonton Furina~ @here",
        "😴 Sudah waktunya mengakhiri babak hari ini. Selamat malam! @here",
        "🛌 Panggung boleh padam, tapi semangat tetap menyala besok pagi! @here",
        "💤 Istirahat yang cukup, bintangku. Furina akan menunggu di hari esok~ @here"
    ]

@tasks.loop(minutes=1)
async def sapa_harian():
    now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone("Asia/Jakarta"))
    channel = bot.get_channel(CHANNEL_ID)

    if channel:
        if now.hour == 7 and now.minute == 0:
            await channel.send(random.choice(pesan_sapa_pagi()))
        elif now.hour == 20 and now.minute == 0:
            await channel.send(random.choice(pesan_sapa_malam()))

@bot.event
async def on_ready():
    print(f"✅ Bot aktif sebagai {bot.user}")
    sapa_harian.start()

# === Web Server for Railway ===
app = Flask('')

@app.route('/')
def home():
    return "Furina bot aktif!"

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# === Jalankan Bot ===
bot.run(TOKEN)
