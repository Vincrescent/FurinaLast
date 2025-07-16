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

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='furina ', intents=intents, help_command=None)

cooldowns = defaultdict(int)

@bot.event
async def on_message(message):
    global cooldowns
    if message.author.bot or not message.guild:
        return

    try:
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
    except Exception as e:
        print(f"--- ERROR PADA SISTEM LEVELING: {e} ---")

    await bot.process_commands(message)

@bot.command(name="halo")
async def sapa_halo(ctx):
    responses = [
        "Hmph, siapa yang memanggil Furina? Baiklah, halo juga~",
        "Furina menyapamu dengan gaya Fontaine yang anggun!",
        "Sebuah sapaan? Menarik! Halo, wahai penonton setiaku.",
        "Oh? Halo. Kuharap kau punya sesuatu yang menarik untuk ditampilkan hari ini.",
        "Panggung terasa lebih hidup dengan kehadiranmu. Halo!"
    ]
    await ctx.send(random.choice(responses))

@bot.command(name="peluk", aliases=["hug"])
async def sapa_peluk(ctx):
    responses = [
        f"E-eh?! Pelukan? B-baiklah... hanya kali ini, ya {ctx.author.mention}...",
        "Kau beruntung Furina sedang baik hati! Ini pelukan spesial dari Archon Hydro~",
        f"Sebuah pelukan hangat untuk aktor favoritku hari ini. Manfaatkan selagi bisa, {ctx.author.mention}.",
        "Hmph. Jangan salah paham. Aku tidak memelukmu. Aku hanya... memeriksa kualitas kostummu dari dekat.",
        f"Baiklah, kemari {ctx.author.mention}. Bahkan seorang sutradara agung sepertiku butuh istirahat sejenak."
    ]
    await ctx.send(random.choice(responses))

@bot.command(name="puji", aliases=["puja"])
async def sapa_puji(ctx):
    responses = [
        "🌟 Hah! Tentu saja aku memujimu! Tapi jangan lupakan siapa yang paling bersinar di sini, yaitu aku!",
        f"✨ {ctx.author.mention}, kau tampil cukup baik hari ini. Jangan mengecewakan panggung Fontaine!",
        f"Kerja bagus, {ctx.author.mention}! Penampilanmu layak mendapatkan tepuk tangan... dariku!",
        "Pujianmu kuakui. Kau punya mata yang bagus untuk melihat kehebatan sejati.",
        f"Teruslah begitu, {ctx.author.mention}, dan mungkin suatu hari kau bisa menjadi sepopuler diriku. Mungkin."
    ]
    await ctx.send(random.choice(responses))

@bot.command()
async def daftar(ctx): #... (kode sama)
    user_id, username = str(ctx.author.id), str(ctx.author)
    if not os.path.exists(FILE_PESERTA): open(FILE_PESERTA, "w").close()
    with open(FILE_PESERTA, "r") as f: daftar_id = [line.strip().split(" ")[-1] for line in f.readlines()]
    if user_id in daftar_id: await ctx.send(f"⚠️ {ctx.author.mention} kamu *sudah terdaftar*.")
    else:
        with open(FILE_PESERTA, "a") as f: f.write(f"{username} {user_id}\n")
        await ctx.send(f"✅ {ctx.author.mention} pendaftaran *berhasil*!")
        
@bot.command()
async def peserta(ctx):
    if not os.path.exists(FILE_PESERTA) or os.path.getsize(FILE_PESERTA) == 0: return await ctx.send("❌ Belum ada peserta.")
    with open(FILE_PESERTA, "r") as f: lines = f.readlines()
    daftar = [f"{i+1}. {line.split(' ')[0]}" for i, line in enumerate(lines)]
    await ctx.send(f"📋 **DAFTAR PESERTA:**\n" + "\n".join(daftar))

@bot.command()
async def hapus(ctx):
    if os.path.exists(FILE_PESERTA):
        os.remove(FILE_PESERTA)
        await ctx.send("🗑️ Semua data peserta telah dihapus.")
    else: await ctx.send("📂 Tidak ada data untuk dihapus.")

@bot.command(name="help")
async def furinahelp(ctx):
    embed = discord.Embed(title="🎭 Daftar Perintah Furina", color=discord.Color.blue(), description="Panggil aku dengan `furina [nama_perintah]`.")
    embed.add_field(name="Interaksi", value="`halo`, `peluk`, `puji`", inline=False)
    embed.add_field(name="Leveling", value="`profil`, `leaderboard`", inline=False)
    embed.add_field(name="Turnamen", value="`daftar`, `peserta`, `hapus`", inline=False)
    embed.add_field(name="Utilitas", value="`voting`, `pilih`, `panggung`, `inspeksi`", inline=False)
    embed.set_footer(text="Gunakan dengan bijak ya~ 💙")
    await ctx.send(embed=embed)

@bot.command(name="profil", aliases=["profile"])
async def profil(ctx, member: discord.Member = None):
    if member is None: member = ctx.author
    try:
        with open(LEVELS_FILE, 'r') as f: users = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): return await ctx.send("🎭 Belum ada data pertunjukan.")
    user_id = str(member.id)
    if user_id in users:
        level, apresiasi = users[user_id].get('level', 1), users[user_id].get('apresiasi', 0)
        dibutuhkan = 5 * (level ** 2) + 50 * level + 100
        persen = min(100, (apresiasi / dibutuhkan) * 100)
        bar = '█' * int(persen / 10) + '░' * (10 - int(persen / 10))
        embed = discord.Embed(title=f"🎭 Kartu Status: {member.display_name}", color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Status Panggung", value=f"Level {level}", inline=True)
        embed.add_field(name="Total Apresiasi", value=f"{apresiasi} poin", inline=True)
        embed.add_field(name="Progres Level", value=f"{bar} ({apresiasi}/{dibutuhkan})", inline=False)
        await ctx.send(embed=embed)
    else: await ctx.send(f"Hmm, {member.mention} sepertinya masih malu-malu.")

@bot.command(name="leaderboard", aliases=["panggung_utama"])
async def leaderboard(ctx):
    try:
        with open(LEVELS_FILE, 'r') as f: users = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): return await ctx.send("🎭 Panggung utama masih kosong.")
    sorted_users = sorted(users.items(), key=lambda item: item[1]['apresiasi'], reverse=True)
    embed = discord.Embed(title="🏆 Panggung Utama Fontaine 🏆", description="Inilah 10 Aktor dengan Apresiasi tertinggi!", color=discord.Color.gold())
    for i, (user_id, data) in enumerate(sorted_users[:10]):
        try:
            member = await ctx.guild.fetch_member(int(user_id))
            nama = member.display_name
        except (discord.NotFound, discord.HTTPException):
            nama = f"Aktor Misterius (ID: {user_id})"
        embed.add_field(name=f"#{i+1}: {nama}", value=f"**Level {data.get('level', 1)}** - {data.get('apresiasi', 0)} Apresiasi", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="voting")
async def voting(ctx, pertanyaan: str, *opsi: str):
    if len(opsi) < 2: return await ctx.send("😤 Berikan minimal 2 opsi.")
    if len(opsi) > 9: return await ctx.send("🎭 Maksimal 9 opsi saja.")
    emoji_angka = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    deskripsi_voting = [f"{emoji_angka[i]} {pilihan}" for i, pilihan in enumerate(opsi)]
    embed = discord.Embed(title=f"📢 VOTING PENTING!", description=f"**{pertanyaan}**\n\n" + "\n".join(deskripsi_voting), color=discord.Color.dark_teal())
    embed.set_footer(text=f"Voting dimulai oleh {ctx.author.display_name}")
    pesan_voting = await ctx.send(embed=embed)
    for i in range(len(opsi)): await pesan_voting.add_reaction(emoji_angka[i])

@bot.command(name="pilih")
async def pilih(ctx, *pilihan: str):
    if len(pilihan) < 2: return await ctx.send("😤 Berikan aku minimal dua pilihan!")
    pilihan_terpilih = random.choice(pilihan)
    embed = discord.Embed(title="👑 KEPUTUSAN AGUNG TELAH DITETAPKAN!", description=f"Aku, Furina, menyatakan bahwa pilihan yang paling layak adalah:\n\n**✨ {pilihan_terpilih} ✨**", color=discord.Color.gold())
    embed.set_footer(text=f"Keputusan dibuat untuk {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command(name="panggung", aliases=["panggeung"])
async def panggung(ctx):
    server = ctx.guild
    owner = server.owner
    if owner is None:
        try: owner = await server.fetch_member(server.owner_id)
        except (discord.NotFound, discord.HTTPException): owner = None
    embed = discord.Embed(title=f"🎭 Panggung Megah: {server.name}!", description="Lihatlah panggung sandiwara yang telah kita bangun bersama ini. Begitu megah, bukan?", color=discord.Color.dark_purple())
    if server.icon: embed.set_thumbnail(url=server.icon.url)
    owner_text = owner.mention if owner else "Tidak dapat ditemukan"
    embed.add_field(name="Sutradara Utama (Owner)", value=owner_text, inline=False)
    embed.add_field(name="Jumlah Penonton (Anggota)", value=f"{server.member_count} jiwa", inline=True)
    embed.add_field(name="Pertunjukan Perdana", value=server.created_at.strftime("%d %B %Y"), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="inspeksi")
async def inspeksi(ctx, member: discord.Member = None):
    if member is None: member = ctx.author
    embed = discord.Embed(title=f"🔍 Hasil Inspeksi Penampilan!", description=f"Hmph! Mari kita lihat lebih dekat penampilan dari {member.mention}...", color=discord.Color.light_grey())
    embed.set_image(url=member.display_avatar.url)
    embed.set_footer(text=f"Diinspeksi oleh Furina atas permintaan {ctx.author.display_name}")
    await ctx.send(embed=embed)

# === Sapa Pagi & Malam (Respons Diperbanyak) ===
def pesan_sapa_pagi():
    return [
        "*Selamat pagi semuanya!* Semoga hari ini penuh kejutan indah dan energi dramatis ala Fontaine! @here",
        "Furina datang membawa semangat! Mari kita mulai hari ini dengan aksi luar biasa! @here",
        "Tirai telah dibuka untuk hari yang baru! Selamat pagi, para bintangku! Saatnya bersinar! @here",
        "Kopi? Teh? Tidak, yang kalian butuhkan adalah semangat dari Archon Hydro untuk memulai hari! Selamat pagi! @here",
        "Bangunlah, para penidur! Panggung kehidupan menanti penampilan terbaikmu hari ini! @here"
    ]

def pesan_sapa_malam():
    return [
        "Malam telah tiba! Jangan lupa istirahat, para penonton Furina~ @here",
        "Sudah waktunya mengakhiri babak hari ini. Selamat malam! @here",
        "Pertunjukan hari ini selesai. Istirahatlah yang nyenyak agar bisa tampil lebih baik besok. Selamat malam! @here",
        "Lampu panggung telah padam. Sampai jumpa di pertunjukan esok hari. Mimpi indah! @here",
        "Bahkan bintang sehebat aku pun butuh istirahat. Selamat malam, semuanya! @here"
    ]

@tasks.loop(minutes=1)
async def sapa_harian():
    now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone("Asia/Jakarta"))
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        if now.hour == 7 and now.minute == 0: await channel.send(random.choice(pesan_sapa_pagi()))
        elif now.hour == 22 and now.minute == 0: await channel.send(random.choice(pesan_sapa_malam()))

# === Event on_ready & Web Server ===
@bot.event
async def on_ready():
    print(f"✅ Bot aktif sebagai {bot.user}")
    sapa_harian.start()

app = Flask('')
@app.route('/')
def home(): return "Furina bot aktif!"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

# === Jalankan Bot ===
bot.run(TOKEN)
