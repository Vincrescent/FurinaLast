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
from PIL import Image, ImageDraw, ImageFont, ImageOps
import requests
import io
import math

def create_circular_avatar(img_url, size=(128, 128)):
    """Mengunduh gambar, mengubahnya menjadi bundar, dan mengembalikan objek Image."""
    response = requests.get(img_url)
    img_bytes = io.BytesIO(response.content)
    img = Image.open(img_bytes).convert("RGBA") 
    
    img = img.resize(size, Image.LANCZOS)
    
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size[0], size[1]), fill=255)
    
    output = ImageOps.fit(img, mask.size, centering=(0.5, 0.5))
    output.putalpha(mask)
    
    return output

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
FILE_PESERTA = "peserta_turnamen.txt"
OWNER_ID=379604922716389408

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

async def grant_exp_and_level_up(member: discord.Member, exp_to_add: int, notification_channel: discord.TextChannel):
    """
    Fungsi terpusat untuk memberikan EXP (Apresiasi) DAN KOIN OPERA, 
    serta menangani kenaikan level.
    """
    if member.bot:
        return

    try:
        user_id = str(member.id)
        loop = asyncio.get_event_loop()
    
        koin_didapat = random.randint(5, 15)

        user_data = await loop.run_in_executor(None, lambda: leveling_collection.find_one({"_id": user_id}))

        if not user_data:
            new_user_data = {
                "_id": user_id, 
                "apresiasi": exp_to_add, 
                "level": 1,
                "koin_opera": koin_didapat,
                "koleksi": [] 
            }
            await loop.run_in_executor(None, lambda: leveling_collection.insert_one(new_user_data))
            user_data = new_user_data
        else:
            await loop.run_in_executor(None, lambda: leveling_collection.update_one(
                {"_id": user_id},
                {"$inc": {"apresiasi": exp_to_add, "koin_opera": koin_didapat}}
            ))

        user_data = await loop.run_in_executor(None, lambda: leveling_collection.find_one({"_id": user_id}))

        level_lama = user_data.get('level', 1)
        current_apresiasi = user_data.get('apresiasi', 0)
        apresiasi_dibutuhkan = 5 * (level_lama ** 2) + 50 * level_lama + 100
        
        if current_apresiasi >= apresiasi_dibutuhkan:
            level_baru = level_lama + 1
            await loop.run_in_executor(None, lambda: leveling_collection.update_one(
                {"_id": user_id},
                {"$set": {"level": level_baru, "apresiasi": 0}} 
            ))
            
            await notification_channel.send(f"🎉 Selamat, {member.mention}! Kau telah naik ke **Level Panggung {level_baru}**!")

            if level_baru in LEVELING_ROLES:
                peran_baru = discord.utils.get(member.guild.roles, name=LEVELING_ROLES[level_baru])
                if peran_baru:
                    await member.add_roles(peran_baru)
                    if level_lama in LEVELING_ROLES:
                        peran_lama = discord.utils.get(member.guild.roles, name=LEVELING_ROLES[level_lama])
                        if peran_lama and peran_lama in member.roles:
                            await member.remove_roles(peran_lama)
                            
    except Exception as e:
        print(f"--- ERROR PADA FUNGSI grant_exp_and_level_up: {e} ---")

async def process_leveling_chat(message):
    """
    Memproses penambahan Apresiasi dari aktivitas chat.
    Sekarang hanya mengurus cooldown dan memanggil fungsi terpusat.
    """
    global chat_cooldowns
    user_id = str(message.author.id)
    now = int(datetime.now().timestamp())

    if now - chat_cooldowns[user_id] > 60:
        chat_cooldowns[user_id] = now
        apresiasi_didapat = random.randint(15, 25)
        await grant_exp_and_level_up(message.author, apresiasi_didapat, message.channel)

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    asyncio.create_task(process_leveling_chat(message))
    await bot.process_commands(message)

@tasks.loop(minutes=1)
async def voice_exp_loop():
    """
    Loop yang berjalan setiap menit untuk memberikan apresiasi kepada anggota
    yang aktif di voice channel bersama orang lain.
    """
    try:
        await bot.wait_until_ready()
        
        main_channel = bot.get_channel(CHANNEL_ID)
        if not main_channel:
            print("Channel ID tidak ditemukan, loop voice EXP tidak bisa berjalan.")
            return
            
        guild = main_channel.guild

        for vc in guild.voice_channels:
            active_members = [m for m in vc.members if not m.bot]

            if len(active_members) >= 2:
                apresiasi_suara = random.randint(5, 15)  
                
                for member in active_members:
                    notification_channel = bot.get_channel(CHANNEL_ID)
                    await grant_exp_and_level_up(member, apresiasi_suara, notification_channel)

    except Exception as e:
        print(f"--- ERROR PADA voice_exp_loop: {e} ---")


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
    loop = asyncio.get_event_loop()
    user_data = await loop.run_in_executor(None, lambda: leveling_collection.find_one({"_id": str(member.id)}))
    
    if not user_data:
        await ctx.send(f"Hmm, {member.mention} sepertinya belum pernah tampil di panggungku.")
        return

    level = user_data.get('level', 1)
    apresiasi = user_data.get('apresiasi', 0)
    koin = user_data.get('koin_opera', 0)
    koleksi = user_data.get('koleksi', []) 
    dibutuhkan = 5 * (level ** 2) + 50 * level + 100
    
    try:
    
        img = Image.open("card_template.png").convert("RGBA") 
        draw = ImageDraw.Draw(img)

        font_regular = ImageFont.truetype("font.ttf", size=24) 
        font_bold = ImageFont.truetype("font_bold.ttf", size=30) 
        font_level = ImageFont.truetype("font_bold.ttf", size=48)
        font_discriminator = ImageFont.truetype("font.ttf", size=20)

        avatar_size = (128, 128)
        avatar_pos = (50, 80)
        
        avatar_circular = create_circular_avatar(member.display_avatar.url, avatar_size)
        img.paste(avatar_circular, avatar_pos, avatar_circular)
        
        text_color = (255, 255, 255, 255)
        level_text = f"Lvl {level}"
        draw.text((30, 30), level_text, font=font_level, fill=text_color) 

        img_width, _ = img.size
        
        discriminator_text = f"#{member.discriminator}" if member.discriminator != "0" else f"#{member.id}"
        text_bbox = font_discriminator.getbbox(discriminator_text)
        text_width = text_bbox[2] - text_bbox[0] 
        draw.text((img_width - text_width - 30, 30), discriminator_text, font=font_discriminator, fill=text_color)
        
        draw.text((avatar_pos[0] + avatar_size[0] + 30, avatar_pos[1] + 20), member.display_name, font=font_bold, fill=text_color)
        
        draw.text((avatar_pos[0], avatar_pos[1] + avatar_size[1] + 20), "Apresiasi", font=font_regular, fill=text_color)

        koin_text = f"🪙 {koin} Koin Opera"
        draw.text((img_width - 250, avatar_pos[1] + avatar_size[1] + 20), koin_text, font=font_regular, fill=text_color)


        bar_start_x = avatar_pos[0] + 150 
        bar_y = avatar_pos[1] + avatar_size[1] + 25
        bar_width = img_width - bar_start_x - 50 
        bar_height = 20
        
        draw.rectangle((bar_start_x, bar_y, bar_start_x + bar_width, bar_y + bar_height), fill=(70, 70, 70, 200))

        if dibutuhkan > 0:
            progress_width = int(bar_width * (apresiasi / dibutuhkan))
            draw.rectangle((bar_start_x, bar_y, bar_start_x + progress_width, bar_y + bar_height), fill=(0, 150, 255, 220)) # Biru
            
        progress_text = f"{apresiasi} / {dibutuhkan}"
        text_bbox = font_regular.getbbox(progress_text)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = bar_start_x + (bar_width - text_width) // 2
        text_y = bar_y + (bar_height - (text_bbox[3] - text_bbox[1])) // 2
        draw.text((text_x, text_y), progress_text, font=font_regular, fill=(255, 255, 255, 255))


        detail_y_start = bar_y + bar_height + 40 
        
        draw.text((avatar_pos[0], detail_y_start), "Apresiasi Saat Ini:", font=font_regular, fill=text_color)
        
        apresiasi_angka_text = str(apresiasi)
        text_bbox = font_regular.getbbox(apresiasi_angka_text)
        text_width = text_bbox[2] - text_bbox[0]
        draw.text((img_width - text_width - 50, detail_y_start), apresiasi_angka_text, font=font_regular, fill=text_color)

        badge_start_x = img_width - 250 
        badge_start_y = detail_y_start + 50 
        badge_spacing_x = 60 
        badge_spacing_y = 60 
        badges_per_row = 3

        for i, item_name in enumerate(koleksi):
            if i >= badges_per_row * 3: 
                break
            
            badge_filename = f"assets/badges/item_{item_name.replace(' ', '_').replace(':', '')}.png"
            try:
                badge_img = Image.open(badge_filename).convert("RGBA")
                badge_img = badge_img.resize((50, 50), Image.LANCZOS)
                
                col = i % badges_per_row
                row = i // badges_per_row
                
                x = badge_start_x + col * badge_spacing_x
                y = badge_start_y + row * badge_spacing_y
                
                img.paste(badge_img, (x, y), badge_img)
            except FileNotFoundError:
                print(f"Peringatan: File badge untuk '{item_name}' tidak ditemukan di '{badge_filename}'")
            except Exception as e:
                print(f"Error saat menempel badge '{item_name}': {e}")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        discord_file = discord.File(buffer, filename="profile.png")
        await ctx.send(file=discord_file)

    except FileNotFoundError as e:
        await ctx.send(f"❌ **Error Aset:** Tidak dapat menemukan file: `{e.filename}`. Pastikan `card_template.png`, `font.ttf`, dan `font_bold.ttf` ada di direktori bot, dan file badge ada di `assets/badges/` jika Anda menggunakannya.")
    except Exception as e:
        await ctx.send(f"Terjadi error saat membuat gambar profil: {e}")
        print(f"Error di profil: {e}")

@bot.command(name="leaderboard", aliases=["panggung_utama"])
async def leaderboard(ctx):
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


PULL_COST = 160 
LOOT_TABLE = [
    {"nama": "Mahkota Sutradara Agung", "tipe": "ITEM", "bobot": 1, "bintang": 5, "emoji": "👑"},
    {"nama": "Pedang Ordo Kehakiman", "tipe": "ITEM", "bobot": 1, "bintang": 5, "emoji": "⚔️"},
    
    {"nama": "Naskah Opera Epik", "tipe": "ITEM", "bobot": 5, "bintang": 4, "emoji": "📜"},
    {"nama": "Kamera Kuno Fontaine", "tipe": "ITEM", "bobot": 5, "bintang": 4, "emoji": "📷"},
    {"nama": "Undangan Pesta Teh Eksklusif", "tipe": "ITEM", "bobot": 5, "bintang": 4, "emoji": "💌"},
    
    {"nama": "50 Koin Opera", "tipe": "KOIN", "bobot": 30, "bintang": 3, "emoji": "🪙"},
    {"nama": "100 Koin Opera", "tipe": "KOIN", "bobot": 20, "bintang": 3, "emoji": "💰"},
    {"nama": "Kue Macaron", "tipe": "ITEM", "bobot": 18, "bintang": 3, "emoji": "🍮"},
    {"nama": "Properci Panggung Rusak", "tipe": "ITEM", "bobot": 15, "bintang": 3, "emoji": "🎭"},
]

@bot.command(name="gachainfo", aliases=["droprate", "listgacha"])
async def gacha_info(ctx):
    """Menampilkan semua item gacha dan probabilitas (rate) mereka."""
    
    embed = discord.Embed(
        title="🎭 Daftar Hadiah Opera Fantastis 🎭", 
        description=f"Setiap pertunjukan (pull) membutuhkan **{PULL_COST} Koin Opera**.",
        color=discord.Color.dark_teal()
    )

    total_weight = sum(item["bobot"] for item in LOOT_TABLE)
    items_by_star = {5: [], 4: [], 3: []}

    for item in LOOT_TABLE:
        nama = item["nama"]
        emoji = item["emoji"]
        bintang = item["bintang"]
        
        percentage = (item["bobot"] / total_weight) * 100
        
        if percentage.is_integer():
            rate_str = f"{int(percentage)}%"
        else:
            rate_str = f"{percentage:.1f}%" 

        line = f"{emoji} **{nama}** - (`{rate_str}`)"
        
        if bintang in items_by_star:
            items_by_star[bintang].append(line)

    if items_by_star[5]:
        embed.add_field(
            name="👑 Bintang 5 (Sangat Langka)", 
            value="\n".join(items_by_star[5]), 
            inline=False
        )
        
    if items_by_star[4]:
        embed.add_field(
            name="✨ Bintang 4 (Langka)", 
            value="\n".join(items_by_star[4]), 
            inline=False
        )
        
    if items_by_star[3]:
        embed.add_field(
            name="⭐ Bintang 3 (Umum)", 
            value="\n".join(items_by_star[3]), 
            inline=False
        )
        
    embed.set_footer(text="Semoga berhasil mendapatkan item favoritmu!")
    await ctx.send(embed=embed)

@bot.command(name="pull", aliases=["gacha"])
async def pull_gacha(ctx):
    user_id = str(ctx.author.id)
    loop = asyncio.get_event_loop()
    
    user_data = await loop.run_in_executor(None, lambda: leveling_collection.find_one({"_id": user_id}))
    
    if not user_data:
        return await ctx.send(f"Hmm, {ctx.author.mention}, kau bahkan belum terdaftar di panggungku. Bicaralah sedikit untuk mendapatkan Koin Opera pertamamu!")

    koin_dimiliki = user_data.get("koin_opera", 0)

    if koin_dimiliki < PULL_COST:
        return await ctx.send(f"Hmph! {ctx.author.mention}, Koin Operamu tidak cukup! Kau butuh **{PULL_COST} Koin** untuk satu pertunjukan. Kau hanya punya **{koin_dimiliki}**.")

    
    hadiah_list = [item for item in LOOT_TABLE]
    bobot_list = [item["bobot"] for item in LOOT_TABLE]
    
    hasil_tarikan = random.choices(hadiah_list, weights=bobot_list, k=1)[0]
    
    await loop.run_in_executor(None, lambda: leveling_collection.update_one(
        {"_id": user_id},
        {"$inc": {"koin_opera": -PULL_COST}}
    ))

    nama_hadiah = hasil_tarikan["nama"]
    tipe_hadiah = hasil_tarikan["tipe"]
    emoji_hadiah = hasil_tarikan["emoji"]
    bintang_hadiah = "⭐" * hasil_tarikan["bintang"]

    embed_title = f"Hasil Pertunjukan Gacha!"
    embed_color = discord.Color.light_grey()    
    
    if tipe_hadiah == "ITEM":
        await loop.run_in_executor(None, lambda: leveling_collection.update_one(
            {"_id": user_id},
            {"$push": {"koleksi": nama_hadiah}}
        ))
        deskripsi_hadiah = f"Kau mendapatkan koleksi baru:\n\n**{emoji_hadiah} {nama_hadiah}**"
        
        if hasil_tarikan["bintang"] == 5:
            embed_title = "👑 PERTUNJUKAN LEGENDA! 👑"
            embed_color = discord.Color.gold()
        elif hasil_tarikan["bintang"] == 4:
            embed_title = "✨ PERTUNJUKAN LUAR BIASA! ✨"
            embed_color = discord.Color.purple()

    elif tipe_hadiah == "KOIN":
        jumlah_koin = int(nama_hadiah.split(" ")[0]) 
        
        await loop.run_in_executor(None, lambda: leveling_collection.update_one(
            {"_id": user_id},
            {"$inc": {"koin_opera": jumlah_koin}}
        ))
        deskripsi_hadiah = f"Kau mendapatkan bonus apresiasi:\n\n**{emoji_hadiah} {nama_hadiah}**"
        embed_color = discord.Color.blue()
        
    embed = discord.Embed(
        title=embed_title,
        description=f"Selamat, {ctx.author.mention}!\n{deskripsi_hadiah}\n\n`{bintang_hadiah}`",
        color=embed_color
    )
    koin_sisa = koin_dimiliki - PULL_COST + (jumlah_koin if tipe_hadiah == "KOIN" else 0)
    embed.set_footer(text=f"Biaya: {PULL_COST} Koin | Sisa Koin: {koin_sisa}")
    
    await ctx.send(embed=embed)

@bot.command(name="givepoint", aliases=["addkoin", "berikoin"])
async def give_point(ctx, member: discord.Member, amount: int):
    """
    Memberikan 'Koin Opera' kepada member.
    Hanya bisa digunakan oleh OWNER_ID.
    """
    
    if ctx.author.id != OWNER_ID:
        return await ctx.send("Hmph! Hanya Sutradara Utama (Owner) yang boleh menggunakan perintah ini!")
        
    if amount <= 0:
        return await ctx.send("Jumlah koin harus lebih dari 0!")
        
    user_id = str(member.id)
    loop = asyncio.get_event_loop()
    
    try:
        user_data = await loop.run_in_executor(None, lambda: leveling_collection.find_one({"_id": user_id}))
        
        if not user_data:
            print(f"Membuat profil baru untuk {member.display_name} via givepoint...")
            new_user_data = {
                "_id": user_id, 
                "apresiasi": 0, 
                "level": 1,
                "koin_opera": amount, 
                "koleksi": []
            }
            await loop.run_in_executor(None, lambda: leveling_collection.insert_one(new_user_data))
        else:
            await loop.run_in_executor(None, lambda: leveling_collection.update_one(
                {"_id": user_id},
                {"$inc": {"koin_opera": amount}}
            ))
            
        await ctx.send(f"✅ **Perintah Sutradara!** Telah ditambahkan **{amount} Koin Opera** ke {member.mention}.")

    except Exception as e:
        await ctx.send(f"Terjadi kesalahan saat mengakses database: {e}")
        print(f"Error pada give_point: {e}")

@give_point.error
async def give_point_error(ctx, error):
    """Error handler untuk perintah give_point"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Format salah! Gunakan: `furina givepoint [@member] [jumlah]`")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("Aku tidak bisa menemukan anggota tersebut.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Jumlah harus berupa angka!")
    elif isinstance(error, commands.CheckFailure):
        pass
    else:
        await ctx.send(f"Terjadi error yang tidak diketahui: {error}")
        print(f"Error pada give_point: {error}")

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
    embed = discord.Embed(
        title="🎭 Daftar Perintah Furina", 
        color=discord.Color.blue(), 
        description="Panggil aku dengan `furina [nama_perintah]`."
    )
    embed.add_field(name="Interaksi", value="`halo`, `peluk`, `puji`", inline=False)
    
    embed.add_field(
        name="Leveling & Gacha 🪙", 
        value="`profil` - Lihat level, koin, dan koleksimu\n"
              "`leaderboard` - Lihat papan peringkat level\n"
              "`pull` / `gacha` - Lakukan gacha (biaya 160 koin)\n"
              "`gachainfo` / `droprate` - Lihat daftar hadiah gacha", 
        inline=False
    )
    embed.add_field(name="Turnamen", value="`daftar`, `peserta`, `hapus`", inline=False)
    embed.add_field(name="Utilitas", value="`voting`, `pilih`, `panggung`, `inspeksi`", inline=False)
    try:
        if ctx.author.id == OWNER_ID:
            embed.add_field(
                name="👑 Khusus Sutradara (Admin)", 
                value="`givepoint` / `addkoin` - Memberi koin ke member", 
                inline=False
            )
    except NameError:        pass 

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

@bot.event
async def on_ready():
    print(f"✅ Bot aktif sebagai {bot.user}")
    sapa_harian.start()
    voice_exp_loop.start()


app = Flask('')
@app.route('/')
def home(): return "Furina bot aktif!"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

bot.run(TOKEN)
