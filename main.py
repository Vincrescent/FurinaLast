import discord
from discord.ext import commands, tasks
from flask import Flask
from threading import Thread
import os
import random
from datetime import datetime
import pytz
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
chat_cooldowns = defaultdict(int)

# =================================================================================
# BAGIAN BARU & MODIFIKASI: FUNGSI LEVELING TERPUSAT
# =================================================================================
async def grant_exp_and_level_up(member: discord.Member, exp_to_add: int, notification_channel: discord.TextChannel):
    """
    Fungsi terpusat untuk memberikan EXP (Apresiasi) dan menangani kenaikan level.
    Bisa digunakan oleh sistem chat, voice, atau sistem lainnya.
    """
    if member.bot:
        return

    try:
        user_id = str(member.id)
        loop = asyncio.get_event_loop()
        
        # Mengambil data pengguna dari database
        user_data = await loop.run_in_executor(None, lambda: leveling_collection.find_one({"_id": user_id}))

        if not user_data:
            await loop.run_in_executor(None, lambda: leveling_collection.insert_one({"_id": user_id, "apresiasi": 0, "level": 1}))
            user_data = {"_id": user_id, "apresiasi": 0, "level": 1}

        # Menambahkan apresiasi baru
        new_apresiasi = user_data.get('apresiasi', 0) + exp_to_add
        level_lama = user_data.get('level', 1)
        
        await loop.run_in_executor(None, lambda: leveling_collection.update_one({"_id": user_id}, {"$set": {"apresiasi": new_apresiasi}}))

        # Pengecekan kenaikan level
        apresiasi_dibutuhkan = 5 * (level_lama ** 2) + 50 * level_lama + 100
        
        if new_apresiasi >= apresiasi_dibutuhkan:
            level_baru = level_lama + 1
            await loop.run_in_executor(None, lambda: leveling_collection.update_one(
                {"_id": user_id},
                {"$set": {"level": level_baru, "apresiasi": 0}} # Reset apresiasi setelah naik level
            ))
            
            await notification_channel.send(f"🎉 Selamat, {member.mention}! Kau telah naik ke **Level Panggung {level_baru}**!")

            # Memberikan role baru jika mencapai level tertentu
            if level_baru in LEVELING_ROLES:
                peran_baru = discord.utils.get(member.guild.roles, name=LEVELING_ROLES[level_baru])
                if peran_baru:
                    await member.add_roles(peran_baru)
                    # Menghapus role lama jika ada
                    if level_lama in LEVELING_ROLES:
                        peran_lama = discord.utils.get(member.guild.roles, name=LEVELING_ROLES[level_lama])
                        if peran_lama and peran_lama in member.roles:
                            await member.remove_roles(peran_lama)
    except Exception as e:
        print(f"--- ERROR PADA FUNGSI grant_exp_and_level_up: {e} ---")

# =================================================================================
# MODIFIKASI: SISTEM LEVELING DARI CHAT
# =================================================================================
async def process_leveling_chat(message):
    """
    Memproses penambahan Apresiasi dari aktivitas chat.
    Sekarang hanya mengurus cooldown dan memanggil fungsi terpusat.
    """
    global chat_cooldowns
    user_id = str(message.author.id)
    now = int(datetime.now().timestamp())

    # Cooldown 60 detik per pengguna untuk mendapatkan Apresiasi dari chat
    if now - chat_cooldowns[user_id] > 60:
        chat_cooldowns[user_id] = now
        apresiasi_didapat = random.randint(15, 25)
        await grant_exp_and_level_up(message.author, apresiasi_didapat, message.channel)

# Event on_message yang telah disederhanakan
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    # Menjalankan proses leveling dari chat secara asynchronous
    asyncio.create_task(process_leveling_chat(message))
    await bot.process_commands(message)

# =================================================================================
# BAGIAN BARU: SISTEM LEVELING DARI VOICE CHANNEL
# =================================================================================
@tasks.loop(minutes=1)
async def voice_exp_loop():
    """
    Loop yang berjalan setiap menit untuk memberikan apresiasi kepada anggota
    yang aktif di voice channel bersama orang lain.
    """
    try:
        # Menunggu bot siap sepenuhnya sebelum menjalankan loop pertama kali
        await bot.wait_until_ready()
        
        # Mengambil channel utama untuk mendapatkan objek guild
        main_channel = bot.get_channel(CHANNEL_ID)
        if not main_channel:
            print("Channel ID tidak ditemukan, loop voice EXP tidak bisa berjalan.")
            return
            
        guild = main_channel.guild

        # Iterasi melalui semua voice channel di server
        for vc in guild.voice_channels:
            # Memfilter anggota yang bukan bot dan tidak sedang mute/deafen server
            # Anda bisa menghapus `not m.voice.self_mute` jika ingin tetap memberi exp walau di-mute
            active_members = [m for m in vc.members if not m.bot]

            # Hanya memberikan Apresiasi jika ada 2 atau lebih orang di channel
            if len(active_members) >= 2:
                apresiasi_suara = random.randint(5, 15)  # EXP lebih kecil dari chat
                
                for member in active_members:
                    # Menggunakan channel notifikasi default untuk pesan level up
                    notification_channel = bot.get_channel(CHANNEL_ID)
                    await grant_exp_and_level_up(member, apresiasi_suara, notification_channel)

    except Exception as e:
        print(f"--- ERROR PADA voice_exp_loop: {e} ---")


# =================================================================================
# KODE LAMA ANDA (TANPA PERUBAHAN)
# ... (Salin semua command Anda dari @bot.command(name="halo") sampai @bot.command(name="inspeksi"))
# =================================================================================

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
        # Menghindari ZeroDivisionError dan memastikan progres tidak melebihi 100% di tampilan
        persen = min(100, (apresiasi / dibutuhkan) * 100) if dibutuhkan > 0 else 0
        bar = '█' * int(persen / 10) + '░' * (10 - int(persen / 10))
        embed = discord.Embed(title=f"🎭 Kartu Status: {member.display_name}", color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Status Panggung", value=f"Level {level}", inline=True)
        embed.add_field(name="Poin Apresiasi", value=f"{apresiasi} poin", inline=True)
        embed.add_field(name="Progres Level Berikutnya", value=f"{bar} ({apresiasi}/{dibutuhkan})", inline=False)
        await ctx.send(embed=embed)
    else: await ctx.send(f"Hmm, {member.mention} sepertinya belum pernah tampil di panggungku.")

@bot.command(name="leaderboard", aliases=["panggung_utama"])
async def leaderboard(ctx):
    # Mengurutkan berdasarkan level, lalu apresiasi
    sorted_users = leveling_collection.find().sort([("level", -1), ("apresiasi", -1)]).limit(10)
    embed = discord.Embed(title="🏆 Panggung Utama Fontaine 🏆", description="Inilah 10 Aktor dengan Level Panggung tertinggi!", color=discord.Color.gold())
    user_list = list(sorted_users)
    if not user_list:
        return await ctx.send("🎭 Panggung utama masih kosong! Belum ada yang mendapatkan apresiasi.")
    
    for i, user_data in enumerate(user_list):
        try:
            member = await ctx.guild.fetch_member(int(user_data["_id"]))
            nama = member.display_name
        except (discord.NotFound, discord.HTTPException):
            nama = f"Aktor Misterius (ID: {user_data['_id']})"
        embed.add_field(name=f"#{i+1}: {nama}", value=f"**Level {user_data.get('level', 1)}** - {user_data.get('apresiasi', 0)} Apresiasi", inline=False)
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


# =================================================================================
# FUNGSI SAPAAN (TANPA PERUBAHAN)
# =================================================================================

def pesan_sapa_pagi():
    return [
        "*Selamat pagi semuanya!* Semoga hari ini penuh kejutan indah dan energi dramatis ala Fontaine!",
        "Furina datang membawa semangat! Mari kita mulai hari ini dengan aksi luar biasa!",
        "Tirai telah dibuka untuk hari yang baru! Selamat pagi, para bintangku! Saatnya bersinar!"
    ]

def pesan_sapa_malam():
    return [
        "Malam telah tiba! Jangan lupa istirahat, para penonton Furina~",
        "Sudah waktunya mengakhiri babak hari ini. Selamat malam!",
        "Pertunjukan hari ini selesai. Istirahatlah yang nyenyak agar bisa tampil lebih baik besok. Selamat malam!"
    ]

@tasks.loop(minutes=1)
async def sapa_harian():
    now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone("Asia/Jakarta"))
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        if now.hour == 7 and now.minute == 0: await channel.send(random.choice(pesan_sapa_pagi()))
        elif now.hour == 22 and now.minute == 0: await channel.send(random.choice(pesan_sapa_malam()))

# =================================================================================
# MODIFIKASI: ON_READY EVENT
# =================================================================================
@bot.event
async def on_ready():
    print(f"✅ Bot aktif sebagai {bot.user}")
    sapa_harian.start()
    voice_exp_loop.start() # <-- BARIS INI DITAMBAHKAN untuk memulai loop voice EXP

# =================================================================================
# KODE UNTUK HOSTING (TANPA PERUBAHAN)
# =================================================================================
app = Flask('')
@app.route('/')
def home(): return "Furina bot aktif!"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

bot.run(TOKEN)
