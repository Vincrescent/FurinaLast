import discord
from discord.ext import commands, tasks
from flask import Flask
from threading import Thread
import os
import random
from datetime import datetime
import pytz
import re
import json
from collections import defaultdict

# --- KONFIGURASI ---
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
FILE_PESERTA = "peserta_turnamen.txt"
LEVELS_FILE = "levels.json"

LEVELING_ROLES = {
    5: "Level 5: Aktor Pendatang Baru",
    10: "Level 10: Figuran Populer",
    20: "Level 20: Aktor Pendukung Utama",
    35: "Level 35: Bintang Panggung",
    50: "Level 50: Idola Fontaine",
    75: "Level 75: Tangan Kanan Sutradara"
}

# --- Inisialisasi Bot ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='furina ', intents=intents, help_command=None)

# --- Variabel Internal ---
cooldowns = defaultdict(int)

# === Event on_message (Sekarang HANYA untuk Leveling) ===
@bot.event
async def on_message(message):
    global cooldowns
    if message.author.bot or not message.guild:
        return

    # Sistem Leveling dijalankan untuk setiap pesan
    try:
        with open(LEVELS_FILE, 'r') as f: users = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): users = {}

    user_id = str(message.author.id)
    if user_id not in users:
        users[user_id] = {'apresiasi': 0, 'level': 1}

    now = int(datetime.now().timestamp())
    if now - cooldowns[user_id] > 60:
        users[user_id]['apresiasi'] += random.randint(15, 25)
        cooldowns[user_id] = now
        
        level_lama = users[user_id]['level']
        apresiasi_dibutuhkan = 5 * (level_lama ** 2) + 50 * level_lama + 100

        if users[user_id]['apresiasi'] >= apresiasi_dibutuhkan:
            users[user_id]['level'] += 1
            level_baru = users[user_id]['level']
            await message.channel.send(f"🎉 Selamat, {message.author.mention}! Kau telah naik ke **Level Panggung {level_baru}**!")
            
            if level_baru in LEVELING_ROLES:
                peran_baru = discord.utils.get(message.guild.roles, name=LEVELING_ROLES[level_baru])
                if peran_baru:
                    await message.author.add_roles(peran_baru)
                    if level_lama in LEVELING_ROLES:
                        peran_lama = discord.utils.get(message.guild.roles, name=LEVELING_ROLES[level_lama])
                        if peran_lama: await message.author.remove_roles(peran_lama)

    with open(LEVELS_FILE, 'w') as f: json.dump(users, f, indent=4)
    
    # Langsung proses perintah tanpa perlu cek sapaan lagi
    await bot.process_commands(message)

# === [PERINTAH BARU] Sapaan yang dijadikan Perintah ===
@bot.command(name="halo")
async def sapa_halo(ctx):
    await ctx.send(random.choice([
        "🎀 Hmph, siapa yang memanggil Furina? Baiklah, halo juga~",
        "💧 Furina menyapamu dengan gaya Fontaine yang anggun!"
    ]))

@bot.command(name="peluk", aliases=["hug"])
async def sapa_peluk(ctx):
    await ctx.send(random.choice([
        f"😳 E-eh?! Pelukan? B-baiklah... hanya kali ini, ya {ctx.author.mention}...",
        "💙 Kau beruntung Furina sedang baik hati! Ini pelukan spesial dari Archon Hydro~"
    ]))

@bot.command(name="puji", aliases=["puja"])
async def sapa_puji(ctx):
    await ctx.send(random.choice([
        "🌟 Hah! Tentu saja aku memujimu! Tapi jangan lupakan siapa yang paling bersinar di sini, yaitu aku!",
        f"✨ {ctx.author.mention}, kau tampil cukup baik hari ini. Jangan mengecewakan panggung Fontaine!"
    ]))

# === Perintah Inti Lainnya (Tidak ada perubahan) ===
@bot.command()
async def daftar(ctx): #... (kode sama)
    user_id = str(ctx.author.id); username = str(ctx.author)
    if not os.path.exists(FILE_PESERTA): open(FILE_PESERTA, "w").close()
    with open(FILE_PESERTA, "r") as f: daftar_id = [line.strip().split(" ")[-1] for line in f.readlines()]
    if user_id in daftar_id: await ctx.send(f"⚠️ {ctx.author.mention} kamu *sudah terdaftar*.")
    else:
        with open(FILE_PESERTA, "a") as f: f.write(f"{username} {user_id}\n")
        await ctx.send(f"✅ {ctx.author.mention} pendaftaran *berhasil*!")

@bot.command()
async def peserta(ctx): #... (kode sama)
    if not os.path.exists(FILE_PESERTA) or os.path.getsize(FILE_PESERTA) == 0: return await ctx.send("❌ Belum ada peserta.")
    with open(FILE_PESERTA, "r") as f: lines = f.readlines()
    daftar = [f"{i+1}. {line.split(' ')[0]}" for i, line in enumerate(lines)]
    await ctx.send(f"📋 **DAFTAR PESERTA:**\n" + "\n".join(daftar))

@bot.command()
async def hapus(ctx): #... (kode sama)
    if os.path.exists(FILE_PESERTA): os.remove(FILE_PESERTA); await ctx.send("🗑️ Semua data peserta telah dihapus.")
    else: await ctx.send("📂 Tidak ada data untuk dihapus.")

@bot.command(name="help")
async def furinahelp(ctx): #... (kode sama, tapi perlu update)
    embed = discord.Embed(title="🎭 Daftar Perintah Furina", description="Panggil aku dengan `furina [nama_perintah]`.\n\n**Perintah Interaksi**\n`halo`, `peluk`, `puji`\n\n**Perintah Leveling**\n`profil`, `leaderboard`\n\n**Perintah Turnamen**\n`daftar`, `peserta`, `hapus`\n\n**Perintah Utilitas**\n`voting`, `pilih`, `panggung`, `inspeksi`\n\n" + "Gunakan dengan bijak ya~ 💙", color=discord.Color.blue())
    await ctx.send(embed=embed)

@bot.command(name="profil") #... (kode sama)
async def profil(ctx, member: discord.Member = None):
    if member is None: member = ctx.author
    try:
        with open(LEVELS_FILE, 'r') as f: users = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): return await ctx.send("🎭 Belum ada data pertunjukan.")
    user_id = str(member.id)
    if user_id in users:
        level, apresiasi = users[user_id].get('level', 1), users[user_id].get('apresiasi', 0)
        dibutuhkan = 5 * (level ** 2) + 50 * level + 100
        persen = (apresiasi / dibutuhkan) * 100
        bar = '█' * int(persen / 10) + '░' * (10 - int(persen / 10))
        embed = discord.Embed(title=f"🎭 Kartu Status: {member.display_name}", color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Status Panggung", value=f"Level {level}", inline=True)
        embed.add_field(name="Apresiasi", value=f"{apresiasi} poin", inline=True)
        embed.add_field(name="Progres Level", value=f"{bar} ({apresiasi}/{dibutuhkan})", inline=False)
        await ctx.send(embed=embed)
    else: await ctx.send(f"Hmm, {member.mention} sepertinya masih malu-malu.")

@bot.command(name="leaderboard", aliases=["panggung_utama"]) #... (kode sama)
async def leaderboard(ctx):
    try:
        with open(LEVELS_FILE, 'r') as f: users = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): return await ctx.send("🎭 Panggung utama masih kosong.")
    sorted_users = sorted(users.items(), key=lambda item: item[1]['apresiasi'], reverse=True)
    embed = discord.Embed(title="🏆 Panggung Utama Fontaine 🏆", description="Inilah 10 Aktor dengan Apresiasi tertinggi!", color=discord.Color.gold())
    for i, (user_id, data) in enumerate(sorted_users[:10]):
        try: member = await ctx.guild.fetch_member(int(user_id)); nama = member.display_name
        except (discord.NotFound, discord.HTTPException): nama = f"Aktor Misterius (ID: {user_id})"
        embed.add_field(name=f"#{i+1}: {nama}", value=f"**Level {data.get('level', 1)}** - {data.get('apresiasi', 0)} Apresiasi", inline=False)
    await ctx.send(embed=embed)

# Sisa kode untuk voting, pilih, panggung, inspeksi, sapa_harian, on_ready, dan web server tidak perlu diubah.
# ... (tempelkan sisa kode Anda di sini)
# ...

@bot.event
async def on_ready():
    print(f"✅ Bot aktif sebagai {bot.user}")
    # Jika Anda punya task sapa_harian, start di sini
    # sapa_harian.start()
app = Flask('')
@app.route('/')
def home(): return "Furina bot aktif!"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()
bot.run(TOKEN)
