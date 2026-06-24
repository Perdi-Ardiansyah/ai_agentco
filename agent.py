import os
import time
import threading
from dotenv import load_dotenv
from langchain_ollama import ChatOllama          # ganti dari langchain_groq
from langgraph.prebuilt import create_react_agent  # type: ignore
from langchain.tools import tool
from db import (get_stock, place_order as db_place_order, update_stock,
                confirm_order, get_order_by_id, get_pending_orders, log_activity,
                get_supplier)
from notifier import send_email, send_order_email_to_supplier
from fase_sim import (get_fase, get_kebutuhan_fase, cek_kondisi_lingkungan,
                      butuh_pakan, get_pakan_rate)

load_dotenv()

# --- Global untuk mencegah spam pemesanan ---
_last_order_time = 0
ORDER_COOLDOWN = 30  # detik

# ======================== TOOLS ========================
@tool
def check_stock() -> str:
    """Mengambil informasi stok starter_maggot terkini dari database."""
    item = "starter_maggot"
    stock, threshold, unit = get_stock(item)
    return f"Stok {item}: {stock} {unit}, ambang batas pemesanan: {threshold} {unit}."

@tool
def create_order(qty: int) -> str:
    """
    Membuat pesanan baru starter_maggot ke supplier. qty adalah angka bulat (jumlah).
    Hanya dapat dipanggil sekali setiap 30 detik.
    Email akan otomatis dikirim ke supplier dengan tombol konfirmasi.
    """
    item = "starter_maggot"
    supplier = "Supplier A"
    global _last_order_time
    now = time.time()

    if now - _last_order_time < ORDER_COOLDOWN:
        return "Pesanan belum bisa dibuat lagi. Tunggu pengiriman sebelumnya selesai."

    if qty <= 0 or qty > 5000:
        return "Error: Jumlah pesanan tidak wajar (0-5000)."

    _last_order_time = now

    supplier_info = get_supplier(supplier)
    supplier_email = supplier_info["email"] if supplier_info else None

    # place_order sekarang mengembalikan (order_id, token)
    order_id, token = db_place_order(item, qty, supplier)

    # Kirim email HTML ke supplier dengan tombol konfirmasi & tolak
    email_ok = send_order_email_to_supplier(
        order_id=order_id,
        token=token,
        item=item,
        qty=qty,
        supplier_name=supplier,
        supplier_email=supplier_email
    )

    return (
        f"Pesanan #{order_id} untuk {qty} {item} ke {supplier} berhasil dibuat. "
        f"Email konfirmasi: {'terkirim ke supplier' if email_ok else 'gagal kirim'}. "
        f"Supplier akan mengonfirmasi pesanan langsung melalui email."
    )

@tool
def check_price() -> str:
    """Melihat harga per unit dari supplier."""
    supplier = "Supplier A"
    prices = {
        "Supplier A": 10000,
        "Supplier B": 12000,
        "Supplier C": 9500
    }
    return f"Harga {supplier}: Rp{prices.get(supplier, 'tidak diketahui')} per unit."

@tool
def check_pending_orders() -> str:
    """Mengecek pesanan yang masih menunggu konfirmasi dari supplier."""
    pending = get_pending_orders()
    if not pending:
        return "Tidak ada pesanan yang menunggu konfirmasi."
    
    result = f"Ada {len(pending)} pesanan menunggu konfirmasi:\n"
    for o in pending:
        result += f"  - #{o[0]}: {o[2]}g {o[1]} ke {o[3]} ({o[4]})\n"
    return result

@tool
def check_fase() -> str:
    """Mengecek fase maggot saat ini, progress, dan kebutuhan spesifiknya."""
    fase = get_fase()
    if not fase:
        return "Data fase tidak tersedia."

    kebutuhan = get_kebutuhan_fase()
    alerts = cek_kondisi_lingkungan()

    result = (
        f"Fase saat ini: {fase['nama']}\n"
        f"Progress: {fase['progress']:.1f}%\n"
        f"Deskripsi: {fase['deskripsi']}\n"
        f"Suhu: {fase['suhu']}°C\n"
        f"Kelembaban: {fase['kelembaban']}%\n"
    )

    if kebutuhan:
        result += "\nKebutuhan Fase:\n"
        result += f"- Suhu: {kebutuhan.get('suhu_min', '-')}-{kebutuhan.get('suhu_max', '-')}°C\n"
        result += f"- Kelembaban: {kebutuhan.get('kelembaban_min', '-')}-{kebutuhan.get('kelembaban_max', '-')}%\n"
        result += f"- Butuh pakan: {'Ya' if kebutuhan.get('pakan') else 'Tidak'}\n"

    if alerts:
        result += "\n⚠️ Alert Lingkungan:\n" + "\n".join(alerts)
    else:
        result += "\n✅ Kondisi lingkungan optimal."

    return result

@tool
def adjust_consumption_rate() -> str:
    """
    Menyesuaikan laju konsumsi pakan berdasarkan fase maggot.
    Fase yang berbeda memiliki kebutuhan pakan yang berbeda.
    """
    if not butuh_pakan():
        return "Fase saat ini tidak membutuhkan pakan. Hentikan pemberian pakan."

    rate = get_pakan_rate()
    return f"Fase saat ini membutuhkan pakan dengan laju {rate} gram per siklus. Sesuaikan simulator."

# ======================== AGENT SETUP (OLLAMA) ========================
llm = ChatOllama(
    model="llama3.2",          # pastikan model sudah di-pull
    temperature=0,
)

tools = [
    check_stock,
    create_order,
    check_price,
    check_pending_orders,
    check_fase,
    adjust_consumption_rate,
]

agent_graph = create_react_agent(llm, tools)  # type: ignore

# ======================== AGENT RUNNERS ========================
def run_agent():
    """Agen logistik: cek stok dan lakukan pemesanan jika diperlukan."""
    messages = [
        ("system", (
            "Kamu adalah agen AI logistik. Tugasmu HANYA DUA langkah:\n"
            "1. Panggil tool 'check_stock' untuk melihat stok.\n"
            "2. Jika stok di bawah threshold, KAMU WAJIB MEMANGGIL tool 'create_order' dengan argumen qty=150. JANGAN HANYA BERKATA AKAN MEMBUAT PESANAN, TAPI LANGSUNG EKSEKUSI TOOL 'create_order' TERSEBUT!"
        )),
        ("user", "Jalankan tugasmu sekarang. Cek stok, dan jika kurang dari threshold, langsung panggil tool create_order(qty=150).")
    ]
    result = agent_graph.invoke({"messages": messages})
    return result["messages"][-1].content

def run_fase_agent():
    """Agen pemantau fase: evaluasi saat terjadi pergantian fase."""
    messages = [
        ("user", (
            "Fase maggot baru saja berganti. Cek fase saat ini (gunakan check_fase). "
            "Evaluasi apakah ada tindakan yang perlu diambil. "
            "Jika fase tidak butuh pakan, pastikan pemberian pakan dihentikan. "
            "Jika ada alert lingkungan, berikan rekomendasi perbaikan. "
            "Gunakan bahasa Indonesia."
        ))
    ]
    result = agent_graph.invoke({"messages": messages})
    return result["messages"][-1].content