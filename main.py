import discord
from discord.ext import commands, tasks
from flask import Flask
from threading import Thread
import os
import random
from datetime import datetime
import pytz
import re
import pymongo
from collections import defaultdict
import asyncio
from dotenv import load_dotenv 

load_dotenv() 

TOKEN = os.getenv("DISCORD_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
FILE_PESERTA = "peserta_turnamen.txt"

LEVELING_ROLES = {
    5: "Level 5: Aktor Pendatang Baru",
    10: "Level 10: Figuran Populer",
    20: "Level 20: Aktor Pendukung Utama",
    35: "Level 35: Bintang Panggung",
    50: "Level 50: Idola Fontaine",
    75: "Level 75: Tangan Kanan Sutradara"
}

try:
    mongo_client = pymongo.MongoClient(MONGO_URI)
    db = mongo_client.get_database("FurinaDB")
    leveling_collection = db.get_collection("leveling")
    print("✅ Berhasil terhubung ke Database MongoDB!")
except pymongo.errors.ConfigurationError:
    print("❌ Gagal terhubung ke Database. Pastikan MONGO_URI sudah benar di file .env Anda.")
    exit()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='furina ', intents=intents, help_command=None)
cooldowns = defaultdict(int)

async def process_leveling(message):
    global cooldowns
    try:
        user_id = str(message.author.id)
        
        loop = asyncio.get_event_loop()
        user_data = await loop.run_in_executor(None, lambda: leveling_collection.find_one({"_id": user_id}))

        if not user_data:
            await loop.run_in_executor(None, lambda: leveling_collection.insert_one({"_id": user_id, "apresiasi": 0, "level": 1}))
            user_data = {"apresiasi": 0, "level": 1}

        now = int(datetime.now().timestamp())
        if now - cooldowns[user_id] > 60:
            apresiasi_didapat = random.randint(15, 25)
            new_apresiasi = user_data.get('apresiasi', 0) + apresiasi_didapat
            cooldowns[user_id] = now
            
            level_lama = user_data.get('level', 1)
            apresiasi_dibutuhkan = 5 * (level_lama ** 2) + 50 * level_lama + 100
            
            await loop.run_in_executor(None, lambda: leveling_collection.update_one({"_id": user_id}, {"$set": {"apresiasi": new_apresiasi}}))

            if new_apresiasi >= apresiasi_dibutuhkan:
                level_baru = level_lama + 1
                await loop.run_in_executor(None, lambda: leveling_collection.update_one({"_id": user_id}, {"$set": {"level": level_baru}}))
                await message.channel.send(f"🎉 Selamat, {message.author.mention}! Kau telah naik ke **Level Panggung {level_baru}**!")
                
                if level_baru in LEVELING_ROLES:
                    peran_baru = discord.utils.get(message.guild.roles, name=LEVELING_ROLES[level_baru])
                    if peran_baru:
                        await message.author.add_roles(peran_baru)
                        if level_lama in LEVELING_ROLES:
                            peran_lama = discord.utils.get(message.guild.roles, name=LEVELING_ROLES[level_lama])
                            if peran_lama and peran_lama in message.author.roles:
                                await message.author.remove_roles(peran_lama)
    except Exception as e:
        print(f"--- ERROR PADA SISTEM LEVELING (DB): {e} ---")

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    asyncio.create_task(process_leveling(message))
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"✅ Bot aktif sebagai {bot.user}")
    
    # Tambahkan ini untuk status "Watching"
    await bot.change_presence(status=discord.Status.dnd, activity=discord.Activity(type=discord.ActivityType.watching, name="In Naga Hitam"))
    
    #sapa_harian.start()

@bot.command(name="halo")
async def sapa_halo(ctx):
    responses = [
        "🎀 Hmph, siapa yang memanggil Furina? Baiklah, halo juga~",
        "💧 Furina menyapamu dengan gaya Fontaine yang anggun!",
        "Sebuah sapaan? Menarik! Halo, wahai penonton setiaku.",
        "Oh? Halo. Kuharap kau punya sesuatu yang menarik untuk ditampilkan hari ini.",
        "Panggung terasa lebih hidup dengan kehadiranmu. Halo!",
        "Ada perlu apa memanggilku? Ah, hanya halo? Baiklah, halo.",
        "Halo! Jangan berdiri di situ saja, panggung menantimu!"
    ]
    await ctx.send(random.choice(responses))

@bot.command(name="peluk", aliases=["hug"])
async def sapa_peluk(ctx):
    responses = [
        f"😳 E-eh?! Pelukan? B-baiklah... hanya kali ini, ya {ctx.author.mention}...",
        "💙 Kau beruntung Furina sedang baik hati! Ini pelukan spesial dari Archon Hydro~",
        f"Sebuah pelukan hangat untuk aktor favoritku hari ini. Manfaatkan selagi bisa, {ctx.author.mention}.",
        "Hmph. Jangan salah paham. Aku tidak memelukmu. Aku hanya... memeriksa kualitas kostummu dari dekat.",
        f"Baiklah, kemari {ctx.author.mention}. Bahkan seorang sutradara agung sepertiku butuh istirahat sejenak.",
        f"Hanya karena kau terlihat menyedihkan, akan kuberikan satu pelukan. Cepat, sebelum aku berubah pikiran, {ctx.author.mention}.",
        "Pelukan? Energi yang bagus! Ini akan menjadi adegan yang dramatis!"
    ]
    await ctx.send(random.choice(responses))

@bot.command(name="puji", aliases=["puja"])
async def sapa_puji(ctx):
    responses = [
        "🌟 Hah! Tentu saja aku memujimu! Tapi jangan lupakan siapa yang paling bersinar di sini, yaitu aku!",
        f"✨ {ctx.author.mention}, kau tampil cukup baik hari ini. Jangan mengecewakan panggung Fontaine!",
        f"Kerja bagus, {ctx.author.mention}! Penampilanmu layak mendapatkan tepuk tangan... dariku!",
        "Pujianmu kuakui. Kau punya mata yang bagus untuk melihat kehebatan sejati.",
        f"Teruslah begitu, {ctx.author.mention}, dan mungkin suatu hari kau bisa menjadi sepopuler diriku. Mungkin.",
        "Tentu saja kau memujiku, siapa lagi yang layak dipuja di sini? Pujianmu diterima.",
        f"Kata-katamu manis sekali, {ctx.author.mention}. Kau tahu cara menyenangkan seorang Ratu."
    ]
    await ctx.send(random.choice(responses))

@bot.command(name="profil", aliases=["profile"])
async def profil(ctx, member: discord.Member = None):
    if member is None: member = ctx.author
    user_data = leveling_collection.find_one({"_id": str(member.id)})
    if user_data:
        level, apresiasi = user_data.get('level', 1), user_data.get('apresiasi', 0)
        dibutuhkan = 5 * (level ** 2) + 50 * level + 100
        persen = min(100, (apresiasi / dibutuhkan) * 100) if dibutuhkan > 0 else 0
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
    sorted_users = leveling_collection.find().sort("apresiasi", -1).limit(10)
    embed = discord.Embed(title="🏆 Panggung Utama Fontaine 🏆", description="Inilah 10 Aktor dengan Apresiasi tertinggi!", color=discord.Color.gold())
    any_user_found = False
    for i, user_data in enumerate(sorted_users):
        any_user_found = True
        try:
            member = await ctx.guild.fetch_member(int(user_data["_id"]))
            nama = member.display_name
        except (discord.NotFound, discord.HTTPException):
            nama = f"Aktor Misterius (ID: {user_data['_id']})"
        embed.add_field(name=f"#{i+1}: {nama}", value=f"**Level {user_data.get('level', 1)}** - {user_data.get('apresiasi', 0)} Apresiasi", inline=False)
    if not any_user_found: return await ctx.send("🎭 Panggung utama masih kosong!")
    await ctx.send(embed=embed)

@bot.command()
async def daftar(ctx):
    user_id, username = str(ctx.author.id), str(ctx.author)
    try:
        if not os.path.exists(FILE_PESERTA): open(FILE_PESERTA, "w").close()
        with open(FILE_PESERTA, "r") as f: daftar_id = [line.strip().split(" ")[-1] for line in f.readlines()]
        if user_id in daftar_id: await ctx.send(f"⚠️ {ctx.author.mention} kamu *sudah terdaftar*.")
        else:
            with open(FILE_PESERTA, "a") as f: f.write(f"{username} {user_id}\n")
            await ctx.send(f"✅ {ctx.author.mention} pendaftaran *berhasil*!")
    except Exception as e:
        await ctx.send("Maaf, terjadi error pada sistem file. Mungkin hosting tidak mendukung penulisan file.")
        print(f"Error pada perintah 'daftar': {e}")

@bot.command()
async def peserta(ctx):
    try:
        if not os.path.exists(FILE_PESERTA) or os.path.getsize(FILE_PESERTA) == 0: return await ctx.send("❌ Belum ada peserta.")
        with open(FILE_PESERTA, "r") as f: lines = f.readlines()
        daftar = [f"{i+1}. {line.split(' ')[0]}" for i, line in enumerate(lines)]
        await ctx.send(f"📋 **DAFTAR PESERTA:**\n" + "\n".join(daftar))
    except Exception as e:
        await ctx.send("Maaf, terjadi error pada sistem file.")
        print(f"Error pada perintah 'peserta': {e}")

@bot.command()
async def hapus(ctx):
    try:
        if os.path.exists(FILE_PESERTA):
            os.remove(FILE_PESERTA)
            await ctx.send("🗑️ Semua data peserta telah dihapus.")
        else: await ctx.send("📂 Tidak ada data untuk dihapus.")
    except Exception as e:
        await ctx.send("Maaf, terjadi error pada sistem file.")
        print(f"Error pada perintah 'hapus': {e}")

@bot.command(name="help")
async def furinahelp(ctx):
    embed = discord.Embed(title="🎭 Daftar Perintah Furina", color=discord.Color.blue(), description="Panggil aku dengan `furina [nama_perintah]`.")
    embed.add_field(name="Interaksi", value="`halo`, `peluk`, `puji`", inline=False)
    embed.add_field(name="Leveling", value="`profil`, `leaderboard`", inline=False)
    embed.add_field(name="Turnamen", value="`daftar`, `peserta`, `hapus`", inline=False)
    embed.add_field(name="Utilitas", value="`voting`, `pilih`, `panggung`, `inspeksi`", inline=False)
    embed.set_footer(text="Gunakan dengan bijak ya~ 💙")
    await ctx.send(embed=embed)

@bot.command(name="voting")
async def voting(ctx, *, argumen: str):
    bagian = [x.strip() for x in argumen.split("|")]
    if len(bagian) < 3:
        return await ctx.send("😤 Format salah. Gunakan: `!voting pertanyaan | opsi1 | opsi2 ...` (minimal 2 opsi)")
    
    pertanyaan = bagian[0]
    opsi = bagian[1:]

    if len(opsi) > 9:
        return await ctx.send("🎭 Maksimal 9 opsi saja.")

    emoji_angka = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    deskripsi_voting = [f"{emoji_angka[i]} {pilihan}" for i, pilihan in enumerate(opsi)]

    embed = discord.Embed(
        title="📢 VOTING PENTING!",
        description=f"**{pertanyaan}**\n\n" + "\n".join(deskripsi_voting),
        color=discord.Color.dark_teal()
    )
    embed.set_footer(text=f"Voting dimulai oleh {ctx.author.display_name}")
    pesan_voting = await ctx.send(embed=embed)

    for i in range(len(opsi)):
        await pesan_voting.add_reaction(emoji_angka[i])


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

def pesan_sapa_pagi():
    return [
        "*Selamat pagi semuanya!* Semoga hari ini penuh kejutan indah dan energi dramatis ala Fontaine! @here",
        "Furina datang membawa semangat! Mari kita mulai hari ini dengan aksi luar biasa! @here",
        "Tirai telah dibuka untuk hari yang baru! Selamat pagi, para bintangku! Saatnya bersinar! @here",
        "Kopi? Teh? Tidak, yang kalian butuhkan adalah semangat dari Archon Hydro untuk memulai hari! Selamat pagi! @here",
        "Bangunlah, para penidur! Panggung kehidupan menanti penampilan terbaikmu hari ini! @here",
        "Fajar menyingsing! Sebuah babak baru telah dimulai. Berikan penampilan terbaikmu hari ini! @here",
        "Selamat pagi, para penonton! Furina sudah siap untuk pertunjukan hari ini. Bagaimana dengan kalian? @here"
    ]

def pesan_sapa_malam():
    return [
        "Malam telah tiba! Jangan lupa istirahat, para penonton Furina~ @here",
        "Sudah waktunya mengakhiri babak hari ini. Selamat malam! @here",
        "Pertunjukan hari ini selesai. Istirahatlah yang nyenyak agar bisa tampil lebih baik besok. Selamat malam! @here",
        "Lampu panggung telah padam. Sampai jumpa di pertunjukan esok hari. Mimpi indah! @here",
        "Bahkan bintang sehebat aku pun butuh istirahat. Selamat malam, semuanya! @here",
        "Bahkan bulan pun butuh istirahat dari sorotan. Selamat malam, sampai jumpa di babak selanjutnya. @here",
        "Tirai malam telah turun. Simpan energimu, karena besok panggung akan lebih megah! Selamat malam! @here"
    ]

@tasks.loop(minutes=1)
async def sapa_harian():
    now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone("Asia/Jakarta"))
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        if now.hour == 7 and now.minute == 0: await channel.send(random.choice(pesan_sapa_pagi()))
        elif now.hour == 22 and now.minute == 0: await channel.send(random.choice(pesan_sapa_malam()))

@bot.event
async def on_ready():
    print(f"✅ Bot aktif sebagai {bot.user}")
    sapa_harian.start()

app = Flask('')
@app.route('/')
def home(): return "Furina bot aktif!"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

bot.run(TOKEN)
