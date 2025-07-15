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

# === Respon Interaktif & Handler Perintah Tanpa Prefix ===
# === GANTI FUNGSI LAMA ANDA DENGAN VERSI BARU YANG LEBIH BAIK INI ===
@bot.event
async def on_message(message):
    # Abaikan pesan dari bot lain, termasuk diri sendiri
    if message.author.bot:
        return

    # Simpan konten asli pesan
    original_content = message.content
    content_lower = original_content.lower()

    # --- Handler untuk perintah tanpa prefix (Versi Perbaikan) ---
    if content_lower.startswith("furina "):
        # Ambil bagian setelah "furina ", lalu tambahkan prefix "f." di depannya
        # Contoh: "furina pilih A B" -> "f. pilih A B"
        new_content = "f." + original_content[len("furina"):] # Potong kata "furina"

        # Buat salinan dari pesan asli dan ganti kontennya
        # Ini cara yang lebih aman daripada mengubah pesan yang sedang diproses
        new_msg = message
        new_msg.content = new_content
        
        print(f"Mengubah '{original_content}' menjadi '{new_msg.content}' untuk diproses.") # Debugging
        
        # Suruh bot untuk memproses pesan yang sudah kita modifikasi
        await bot.process_commands(new_msg)
        return # Penting: Hentikan fungsi di sini agar tidak lanjut ke bawah

    # --- Logika sapaan (hanya berjalan jika logika di atas tidak terpanggil) ---
    mentioned = bot.user in message.mentions or "furina" in content_lower
    if mentioned:
        if re.search(r"\bhalo\b", content_lower):
            responses = [
                "🎀 Hmph, siapa yang memanggil Furina? Baiklah, halo juga~",
                "💧 Furina menyapamu dengan gaya Fontaine yang anggun!",
            ]
            await message.channel.send(random.choice(responses))
            return

        if re.search(r"\b(hug|peluk)\b", content_lower):
            responses = [
                f"😳 E-eh?! Pelukan? B-baiklah... hanya kali ini, ya {message.author.mention}...",
                "💙 Kau beruntung Furina sedang baik hati! Ini pelukan spesial dari Archon Hydro~",
            ]
            await message.channel.send(random.choice(responses))
            return

        if re.search(r"\b(puji|puja)\b", content_lower):
            responses = [
                "🌟 Hah! Tentu saja aku memujimu! Tapi jangan lupakan siapa yang paling bersinar di sini, yaitu aku!",
                f"✨ {message.author.mention}, kau tampil cukup baik hari ini. Jangan mengecewakan panggung Fontaine!",
            ]
            await message.channel.send(random.choice(responses))
            return

    # Proses perintah dengan prefix "f." secara normal jika tidak ada kondisi di atas yang cocok
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

@bot.command(name="furinahelp")
async def furinahelp(ctx):
    embed = discord.Embed(
        title="🎭 Daftar Perintah Furina",
        description=(
            "**Prefix Command**\n"
            "`f.daftar`, `f.peserta`, `f.hapus`, `f.tes`, `f.voting`, `f.pilih`, `f.panggung`, `f.inspeksi`, `f.furinahelp`\n\n"
            "**Tanpa Prefix (Sapaan)**\n"
            "`halo furina`, `hug furina`, `puji furina`\n\n"
            "**Tanpa Prefix (Perintah)**\n"
            "Gunakan `furina [nama_perintah]`, contoh: `furina pilih opsi1 opsi2`\n\n"
            "Gunakan dengan bijak ya~ 💙"
        ),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

# === [PERINTAH BARU] ===
@bot.command(name="voting")
async def voting(ctx, pertanyaan: str, *opsi: str):
    if len(opsi) < 2:
        await ctx.send("😤 Sebuah pilihan bukanlah pilihan jika hanya ada satu! Berikan minimal 2 opsi.")
        return
    if len(opsi) > 9:
        await ctx.send("🎭 Terlalu banyak pilihan akan membuat panggung berantakan! Maksimal 9 opsi saja.")
        return

    emoji_angka = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
    
    deskripsi_voting = []
    for i, pilihan in enumerate(opsi):
        deskripsi_voting.append(f"{emoji_angka[i]} {pilihan}")

    embed = discord.Embed(
        title=f"📢 PERHATIAN! SEBUAH VOTING PENTING!",
        description=f"**{pertanyaan}**\n\nAku, Furina, menuntut jawaban dari kalian semua! Pilihlah dengan bijak, karena setiap pilihan menentukan babak selanjutnya.\n\n" + "\n".join(deskripsi_voting),
        color=discord.Color.dark_teal()
    )
    embed.set_footer(text=f"Voting dimulai oleh {ctx.author.display_name}")

    pesan_voting = await ctx.send(embed=embed)

    for i in range(len(opsi)):
        await pesan_voting.add_reaction(emoji_angka[i])

@bot.command(name="pilih")
async def pilih(ctx, *pilihan: str):
    if len(pilihan) < 2:
        await ctx.send("😤 Apa yang harus kupilih jika opsinya hanya satu?! Berikan aku minimal dua pilihan untuk kupertimbangkan!")
        return

    pilihan_terpilih = random.choice(pilihan)

    kalimat_pembuka = [
        "Setelah melalui pertimbangan yang sangat mendalam di bawah sorotan panggung...",
        "Dengan kekuatan dan kebijaksanaanku sebagai seorang Archon...",
        "Dengarkan! Keputusan final telah dibuat dan tidak dapat diganggu gugat...",
        "Hmph, pilihan yang mudah untuk seseorang sejenius diriku...",
    ]

    embed = discord.Embed(
        title="👑 KEPUTUSAN AGUNG TELAH DITETAPKAN!",
        description=(
            f"{random.choice(kalimat_pembuka)}\n\n"
            f"Aku, Furina, dengan ini menyatakan bahwa pilihan yang paling layak adalah:\n\n"
            f"**✨ {pilihan_terpilih} ✨**\n\n"
            "Sekarang, laksanakan! Jangan membuatku menunggu!"
        ),
        color=discord.Color.from_rgb(255, 215, 0)
    )
    embed.set_footer(text=f"Keputusan dibuat untuk {ctx.author.display_name}")
    await ctx.send(embed=embed)

@bot.command(name="panggung")
async def panggung(ctx):
    server = ctx.guild
    jumlah_member = server.member_count
    owner = server.owner
    tanggal_dibuat = server.created_at.strftime("%d %B %Y")

    embed = discord.Embed(
        title=f"🎭 Selamat Datang di Panggung Megah: {server.name}!",
        description="Lihatlah panggung sandiwara yang telah kita bangun bersama ini. Begitu megah, bukan? Tentu saja, karena ada aku di sini!",
        color=discord.Color.dark_purple()
    )
    embed.set_thumbnail(url=server.icon.url if server.icon else None)
    embed.add_field(name="Sutradara Utama (Owner)", value=owner.mention, inline=False)
    embed.add_field(name="Jumlah Penonton (Anggota)", value=f"{jumlah_member} jiwa", inline=True)
    embed.add_field(name="Pertunjukan Perdana (Dibuat pada)", value=tanggal_dibuat, inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="inspeksi")
async def inspeksi(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    embed = discord.Embed(
        title=f"🔍 Hasil Inspeksi Penampilan!",
        description=f"Hmph! Mari kita lihat lebih dekat penampilan dari {member.mention}...",
        color=discord.Color.from_rgb(173, 216, 230)
    )
    embed.set_image(url=member.display_avatar.url)
    embed.set_footer(text=f"Diinspeksi oleh Furina atas permintaan {ctx.author.display_name}")
    
    await ctx.send(embed=embed)


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
