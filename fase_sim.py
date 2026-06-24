from db import get_fase, update_fase, get_stock, get_all_fase_data, update_env_data
import time

# Konfigurasi fase (durasi dalam detik untuk demo, ubah ke hari untuk nyata)
FASE_CONFIG = {
    "telur": {
        "durasi": 30,        # 30 detik untuk demo (normal: 3 hari)
        "next": "larva_muda",
        "kebutuhan": {
            "suhu_min": 27,
            "suhu_max": 30,
            "kelembaban_min": 70,
            "kelembaban_max": 80,
            "pakan": False    # tidak perlu pakan
        },
        "deskripsi": "Telur BSF sedang dalam masa inkubasi"
    },
    "larva_muda": {
        "durasi": 45,        # 45 detik untuk demo
        "next": "larva_dewasa",
        "kebutuhan": {
            "suhu_min": 28,
            "suhu_max": 32,
            "kelembaban_min": 65,
            "kelembaban_max": 80,
            "pakan": True,    # perlu starter_maggot
            "pakan_item": "starter_maggot",
            "pakan_rate": 2.0  # gram per siklus
        },
        "deskripsi": "Larva muda butuh pakan starter secara teratur"
    },
    "larva_dewasa": {
        "durasi": 60,        # 60 detik untuk demo
        "next": "pre_pupa",
        "kebutuhan": {
            "suhu_min": 26,
            "suhu_max": 34,
            "kelembaban_min": 60,
            "kelembaban_max": 80,
            "pakan": True,
            "pakan_item": "starter_maggot",
            "pakan_rate": 5.0  # konsumsi lebih besar
        },
        "deskripsi": "Larva dewasa mengkonsumsi pakan dalam jumlah besar"
    },
    "pre_pupa": {
        "durasi": 25,        # 25 detik
        "next": "pupa",
        "kebutuhan": {
            "suhu_min": 25,
            "suhu_max": 30,
            "kelembaban_min": 50,
            "kelembaban_max": 70,
            "pakan": False   # tidak makan
        },
        "deskripsi": "Pre-pupa mulai bermigrasi, hentikan pemberian pakan"
    },
    "pupa": {
        "durasi": 40,        # 40 detik
        "next": "lalat_dewasa",
        "kebutuhan": {
            "suhu_min": 25,
            "suhu_max": 28,
            "kelembaban_min": 50,
            "kelembaban_max": 70,
            "pakan": False
        },
        "deskripsi": "Pupa dalam masa metamorfosis, jangan diganggu"
    },
    "lalat_dewasa": {
        "durasi": 35,        # 35 detik
        "next": "telur",     # kembali ke awal (siklus baru)
        "kebutuhan": {
            "suhu_min": 27,
            "suhu_max": 30,
            "kelembaban_min": 60,
            "kelembaban_max": 75,
            "pakan": False,  # lalat hanya butuh air gula
            "butuh_kawin": True
        },
        "deskripsi": "Lalat dewasa siap kawin dan bertelur"
    }
}

# Data lingkungan (simulasi, nanti diganti sensor)
ENV_DATA = {
    "suhu": 29.0,
    "kelembaban": 75.0,
    "cahaya": True
}

def init_fase():
    """Inisialisasi data fase jika belum ada"""
    fase = get_fase()
    if fase is None:
        update_fase(
            nama="telur",
            progress=0,
            deskripsi=FASE_CONFIG["telur"]["deskripsi"]
        )
        # Set suhu dan kelembaban dari env data
        update_env_data(ENV_DATA["suhu"], ENV_DATA["kelembaban"], ENV_DATA["cahaya"])

def get_kebutuhan_fase():
    """Dapatkan kebutuhan fase saat ini"""
    fase = get_fase()
    if fase is None:
        return None
    nama_fase = str(fase["nama"])
    config = FASE_CONFIG.get(nama_fase, {})
    kebutuhan = config.get("kebutuhan", {}) if isinstance(config, dict) else {}
    return kebutuhan

def update_fase_progress():
    """
    Update progress fase. Jika progress >= 100, pindah ke fase berikutnya.
    Return True jika fase berganti, False jika masih berjalan.
    """
    fase = get_fase()
    if fase is None:
        init_fase()
        return False

    nama = str(fase["nama"])
    config = FASE_CONFIG.get(nama)
    if not config:
        return False

    durasi = int(config["durasi"])  # pyrefly: ignore[bad-argument-type]
    progress_baru = float(fase["progress"]) + (100.0 / durasi)  # kenaikan per panggilan

    if progress_baru >= 100:
        # Pindah ke fase berikutnya
        next_fase = str(config["next"])
        update_fase(
            nama=next_fase,
            progress=0,
            deskripsi=FASE_CONFIG[next_fase]["deskripsi"]  # pyrefly: ignore
        )
        print(f"🔄 Fase berganti: {fase['nama']} → {next_fase}")
        return True
    else:
        update_fase(
            nama=fase["nama"],
            progress=progress_baru,
            deskripsi=fase["deskripsi"]
        )
        return False

def cek_kondisi_lingkungan():
    """Cek apakah kondisi lingkungan sesuai dengan kebutuhan fase"""
    kebutuhan = get_kebutuhan_fase()
    if not kebutuhan:
        return []

    alerts = []
    if ENV_DATA["suhu"] < kebutuhan.get("suhu_min", 0):
        alerts.append(f"⚠️ Suhu terlalu rendah: {ENV_DATA['suhu']}°C (min: {kebutuhan['suhu_min']}°C)")
    if ENV_DATA["suhu"] > kebutuhan.get("suhu_max", 100):
        alerts.append(f"⚠️ Suhu terlalu tinggi: {ENV_DATA['suhu']}°C (max: {kebutuhan['suhu_max']}°C)")
    if ENV_DATA["kelembaban"] < kebutuhan.get("kelembaban_min", 0):
        alerts.append(f"⚠️ Kelembaban terlalu rendah: {ENV_DATA['kelembaban']}% (min: {kebutuhan['kelembaban_min']}%)")
    if ENV_DATA["kelembaban"] > kebutuhan.get("kelembaban_max", 100):
        alerts.append(f"⚠️ Kelembaban terlalu tinggi: {ENV_DATA['kelembaban']}% (max: {kebutuhan['kelembaban_max']}%)")
    return alerts

def butuh_pakan():
    """Apakah fase saat ini butuh pakan?"""
    kebutuhan = get_kebutuhan_fase()
    if not kebutuhan:
        return False
    return kebutuhan.get("pakan", False)

def get_pakan_rate():
    """Berapa laju konsumsi pakan di fase ini?"""
    kebutuhan = get_kebutuhan_fase()
    if not kebutuhan:
        return 0
    return kebutuhan.get("pakan_rate", 0)