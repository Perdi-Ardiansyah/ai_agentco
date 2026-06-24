import sys
import io
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
import time
import threading
from db import init_db, get_stock, get_fase, get_pending_orders, timeout_order
from simulator import simulate_consumption
from fase_sim import init_fase, update_fase_progress, butuh_pakan, cek_kondisi_lingkungan, get_pakan_rate
from agent import run_agent, run_fase_agent
from notifier import send_email
from confirm_server import run_confirm_server

THRESHOLD = 50
pending_wait_counts = {}

def run_simulation_step():
    logs = []
    
    # 1. Update progres fase
    fase_berganti = update_fase_progress()
    fase = get_fase()
    if not fase:
        return logs

    # 2. Cek kondisi lingkungan
    alerts = cek_kondisi_lingkungan()
    if alerts:
        for alert in alerts:
            logs.append(alert)

    # 3. Simulasi konsumsi pakan (hanya jika fase butuh)
    if butuh_pakan():
        pakan_rate = get_pakan_rate()
        simulate_consumption(item="starter_maggot", consumption_rate=pakan_rate)
        stock, thresh, unit = get_stock("starter_maggot")
        logs.append(f"🧬 Fase: {fase['nama']} ({fase['progress']:.1f}%) | 📦 Stok: {stock} {unit}")
    else:
        stock, thresh, unit = get_stock("starter_maggot")
        logs.append(f"🧬 Fase: {fase['nama']} ({fase['progress']:.1f}%) | ⏸️  Tidak butuh pakan")

    # 4. Jika fase berganti, panggil agen untuk evaluasi
    if fase_berganti:
        logs.append(f"\n🔄 Fase baru: {fase['nama']}")
        logs.append("Memanggil agen untuk evaluasi fase...")
        response = run_fase_agent()
        logs.append(f"✅ Agen: {response}\n")

    # 5. Cek threshold stok (wajib cek meskipun fase tidak butuh pakan)
    if stock <= thresh:
        pending = get_pending_orders()
        if pending:
            all_timeout = False
            for p in pending:
                order_id = p[0]
                if order_id not in pending_wait_counts:
                    pending_wait_counts[order_id] = 0
                
                pending_wait_counts[order_id] += 1
                
                if pending_wait_counts[order_id] > 3:
                    logs.append(f"⏳ Pesanan #{order_id} sudah menunggu lebih dari 3 kali. Membatalkan pesanan lama...")
                    timeout_order(order_id)
                    del pending_wait_counts[order_id]
                    all_timeout = True
                else:
                    logs.append(f"⏳ Stok di bawah threshold, pesanan #{order_id} menunggu konfirmasi supplier (Penungguan {pending_wait_counts[order_id]}/3).")
            
            if all_timeout:
                logs.append("⚠️  Pesanan sebelumnya timeout. Memanggil agen logistik untuk mengirim ulang email baru...")
                logs.append("📧 Email dengan tombol konfirmasi akan dikirim ke supplier...")
                response = run_agent()
                logs.append(f"✅ Agen Logistik: {response}\n")
        else:
            logs.append("⚠️  Stok di bawah threshold! Memanggil agen logistik...")
            logs.append("📧 Email dengan tombol konfirmasi akan dikirim ke supplier...")
            response = run_agent()
            logs.append(f"✅ Agen Logistik: {response}\n")
    elif not butuh_pakan():
        logs.append("✅ Fase tidak butuh pakan, status: stok aman.\n")
    else:
        logs.append("✅ Status: stok aman.\n")

    return logs

def main():
    init_db()
    init_fase()

    # Jalankan Flask confirm server di background thread
    server_thread = threading.Thread(target=run_confirm_server, daemon=True)
    server_thread.start()
    time.sleep(1)  # tunggu server siap

    print("=" * 60)
    print("🤖 Sistem Agentic AI TPS 3R (Ollama + Email Konfirmasi)")
    print("🌐 Confirm Server: http://localhost:5050")
    print("=" * 60)

    # Tampilkan fase awal
    fase = get_fase()
    if fase:
        print(f"🧬 Fase awal: {fase['nama']} | {fase['deskripsi']}")
    print("-" * 60)

    while True:
        logs = run_simulation_step()
        for log in logs:
            print(log)
        time.sleep(10)

if __name__ == "__main__":
    main()