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

# === [PERBAIKAN] Mengaktifkan semua Intent yang dibutuhkan ===
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # Penting untuk mendapatkan data anggota

# === [PERBAIKAN] Menonaktifkan command help bawaan ===
bot = commands.Bot(command_prefix='furina ', intents=intents, help_command=None)

FILE_PESERTA = "peserta_turnamen.txt"

# === Respon Interaktif Tanpa Prefix (Sapaan) ===
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not message.content.lower().startswith(bot.command_prefix):
        content_lower = message.content.lower()
        mentioned = bot.user in message.mentions or "furina" in content_lower
        if mentioned:
            if re.search(r"\bhalo\b", content_lower):
                await message.channel.send(random.choice([
                    "🎀 Hmph, siapa yang memanggil Furina? Baiklah, halo juga~",
                    "💧 Furina menyapamu dengan gaya Fontaine yang anggun!"
                ]))
                return
            if re.search(r"\b(hug|peluk)\b", content_lower):
                await message.channel.send(random.choice([
                    f"😳 E-eh?! Pelukan? B-baiklah... hanya kali ini, ya {message.author.mention}...",
                    "💙 Kau beruntung Furina sedang baik hati! Ini pelukan spesial dari Archon Hydro~"
                ]))
                return
            if re.search(r"\b(puji|puja)\b", content_lower):
                await message.channel.send(random.choice([
                    "🌟 Hah! Tentu saja aku memujimu! Tapi jangan lupakan siapa yang paling bersinar di sini, yaitu aku!",
                    f"✨ {message.author.mention}, kau tampil cukup baik hari ini. Jangan mengecewakan panggung Fontaine!"
                ]))
                return
                
    await bot.process_commands(message)

# === Perintah Inti ===
@bot.command()
async def daftar(ctx):
    # ... (kode ini tidak berubah)
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
    # ... (kode ini tidak berubah)
    if not os.path.exists(FILE_PESERTA) or os.path.getsize(FILE_PESERTA) == 0:
        await ctx.send("❌ Belum ada peserta yang mendaftar.")
        return
    with open(FILE_PESERTA, "r") as f:
        lines = f.readlines()
    daftar = [f"{i+1}. {line.split(' ')[0]}" for i, line in enumerate(lines)]
    await ctx.send(f"📋 **DAFTAR PESERTA TURNAMEN:**\n" + "\n".join(daftar))

@bot.command()
async def hapus(ctx):
    # ... (kode ini tidak berubah)
    if os.path.exists(FILE_PESERTA):
        os.remove(FILE_PESERTA)
        await ctx.send("🗑️ Semua data peserta telah dihapus.")
    else:
        await ctx.send("📂 Tidak ada data untuk dihapus.")

@bot.command(name="help")
async def furinahelp(ctx):
    # ... (kode ini tidak berubah)
    embed = discord.Embed(title="🎭 Daftar Perintah Furina", description="Panggil aku dengan `furina [nama_perintah]`.\n\n**Perintah Turnamen**\n`daftar`, `peserta`, `hapus`\n\n**Perintah Utilitas**\n`voting`, `pilih`, `panggung`, `inspeksi`\n\n**Sapaan (Tanpa Perintah)**\nAku juga merespon jika kamu menyapaku dengan `halo`, `peluk`, atau `puji`.\n\n" + "Gunakan dengan bijak ya~ 💙", color=discord.Color.blue())
    await ctx.send(embed=embed)

@bot.command(name="voting")
async def voting(ctx, pertanyaan: str, *opsi: str):
    # ... (kode ini tidak berubah)
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
    # ... (kode ini tidak berubah)
    if len(pilihan) < 2: return await ctx.send("😤 Berikan aku minimal dua pilihan!")
    pilihan_terpilih = random.choice(pilihan)
    embed = discord.Embed(title="👑 KEPUTUSAN AGUNG TELAH DITETAPKAN!", description=f"Aku, Furina, menyatakan bahwa pilihan yang paling layak adalah:\n\n**✨ {pilihan_terpilih} ✨**", color=discord.Color.gold())
    embed.set_footer(text=f"Keputusan dibuat untuk {ctx.author.display_name}")
    await ctx.send(embed=embed)

# === [PERBAIKAN] Perintah panggung versi paling stabil ===
@bot.command(name="panggung")
async def panggung(ctx):
    server = ctx.guild
    owner = server.owner
    if owner is None:
        try:
            owner = await server.fetch_member(server.owner_id)
        except (discord.NotFound, discord.HTTPException):
            owner = None
    embed = discord.Embed(title=f"🎭 Panggung Megah: {server.name}!", description="Lihatlah panggung sandiwara yang telah kita bangun bersama ini. Begitu megah, bukan?", color=discord.Color.dark_purple())
    if server.icon: embed.set_thumbnail(url=server.icon.url)
    owner_text = owner.mention if owner else "Tidak dapat ditemukan"
    embed.add_field(name="Sutradara Utama (Owner)", value=owner_text, inline=False)
    embed.add_field(name="Jumlah Penonton (Anggota)", value=f"{server.member_count} jiwa", inline=True)
    embed.add_field(name="Pertunjukan Perdana", value=server.created_at.strftime("%d %B %Y"), inline=True)
    await ctx.send(embed=embed)

@bot.command(name="inspeksi")
async def inspeksi(ctx, member: discord.Member = None):
    # ... (kode ini tidak berubah)
    if member is None: member = ctx.author
    embed = discord.Embed(title=f"🔍 Hasil Inspeksi Penampilan!", description=f"Hmph! Mari kita lihat lebih dekat penampilan dari {member.mention}...", color=discord.Color.light_grey())
    embed.set_image(url=member.display_avatar.url)
    embed.set_footer(text=f"Diinspeksi oleh Furina atas permintaan {ctx.author.display_name}")
    await ctx.send(embed=embed)

# === Sapa Pagi & Malam ===
# ... (kode ini tidak berubah)
def pesan_sapa_pagi(): return ["🎭 *Selamat pagi semuanya!* Semoga hari ini penuh kejutan indah! @here", "🌊 Furina datang membawa semangat! Mari kita mulai hari ini dengan aksi luar biasa! @here"]
def pesan_sapa_malam(): return ["🌙 Malam telah tiba! Jangan lupa istirahat, para penonton Furina~ @here", "😴 Sudah waktunya mengakhiri babak hari ini. Selamat malam! @here"]
@tasks.loop(minutes=1)
async def sapa_harian():
    now = datetime.utcnow().replace(tzinfo=pytz.utc).astimezone(pytz.timezone("Asia/Jakarta"))
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        if now.hour == 7 and now.minute == 0: await channel.send(random.choice(pesan_sapa_pagi()))
        elif now.hour == 22 and now.minute == 0: await channel.send(random.choice(pesan_sapa_malam()))

# === Event on_ready & Web Server ===
# ... (kode ini tidak berubah)
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
