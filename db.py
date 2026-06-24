import sqlite3
import uuid
from datetime import datetime

DB = "tps.db"

# ============================================================
# INISIALISASI DATABASE (JALANKAN SEKALI SAAT APLIKASI MULAI)
# ============================================================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # --- Tabel Inventaris ---
    c.execute('''CREATE TABLE IF NOT EXISTS inventory
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  item TEXT UNIQUE,
                  stock REAL,
                  threshold REAL,
                  unit TEXT)''')

    # --- Tabel Pesanan (updated with token) ---
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  item TEXT,
                  qty REAL,
                  supplier TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  status TEXT,
                  confirm_token TEXT UNIQUE,
                  confirmed_at DATETIME,
                  confirmed_by TEXT,
                  supplier_note TEXT)''')

    # --- Tabel Roles / Users ---
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  email TEXT UNIQUE,
                  role TEXT,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    # --- Tabel Supplier ---
    c.execute('''CREATE TABLE IF NOT EXISTS suppliers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE,
                  email TEXT,
                  phone TEXT,
                  address TEXT,
                  is_active INTEGER DEFAULT 1)''')

    # --- Tabel Log Aktivitas ---
    c.execute('''CREATE TABLE IF NOT EXISTS activity_log
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  action TEXT,
                  detail TEXT,
                  actor TEXT,
                  role TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    # --- Tabel Fase Maggot ---
    c.execute('''CREATE TABLE IF NOT EXISTS fase_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nama TEXT,
                  progress REAL,
                  deskripsi TEXT,
                  suhu REAL,
                  kelembaban REAL,
                  cahaya INTEGER)''')

    # --- Isi data awal inventory jika kosong ---
    c.execute("SELECT COUNT(*) FROM inventory")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO inventory (item, stock, threshold, unit) VALUES (?,?,?,?)",
                  ("starter_maggot", 200, 50, "gram"))

    # --- Isi data awal fase jika kosong ---
    c.execute("SELECT COUNT(*) FROM fase_data")
    if c.fetchone()[0] == 0:
        c.execute('''INSERT INTO fase_data 
                     (nama, progress, deskripsi, suhu, kelembaban, cahaya) 
                     VALUES (?,?,?,?,?,?)''',
                  ("telur", 0.0, "Telur BSF dalam masa inkubasi", 29.0, 75.0, 1))

    # --- Isi data awal users (admin & supplier) ---
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (name, email, role) VALUES (?,?,?)",
                  ("Admin TPS 3R", "admin@tps3r.local", "admin"))
        c.execute("INSERT INTO users (name, email, role) VALUES (?,?,?)",
                  ("Supplier A", "raiqudrat17@gmail.com", "supplier"))

    # --- Isi data awal supplier ---
    c.execute("SELECT COUNT(*) FROM suppliers")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO suppliers (name, email, phone, address) VALUES (?,?,?,?)",
                  ("Supplier A", "raiqudrat17@gmail.com", "08123456789", "Jl. Supplier No. 1"))

    conn.commit()
    conn.close()


# ============================================================
# FUNGSI INVENTARIS (LOGISTIK PAKAN)
# ============================================================
def get_stock(item="starter_maggot"):
    """Ambil data stok, threshold, dan satuan untuk item tertentu."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT stock, threshold, unit FROM inventory WHERE item=?", (item,))
    row = c.fetchone()
    conn.close()
    if row:
        return row  # (stock, threshold, unit)
    return (0, 0, "")

def update_stock(item, new_stock):
    """Perbarui stok item (nilai absolut)."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE inventory SET stock=? WHERE item=?", (new_stock, item))
    conn.commit()
    conn.close()


# ============================================================
# FUNGSI PEMESANAN (ORDERS) - DENGAN TOKEN KONFIRMASI
# ============================================================
def place_order(item, qty, supplier="Supplier A"):
    """Catat pesanan baru dengan status 'dipesan' dan generate token konfirmasi."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    token = str(uuid.uuid4())
    c.execute(
        "INSERT INTO orders (item, qty, supplier, status, confirm_token) VALUES (?,?,?,?,?)",
        (item, qty, supplier, "dipesan", token)
    )
    order_id = c.lastrowid
    conn.commit()
    conn.close()

    # Log aktivitas
    log_activity("CREATE_ORDER", f"Pesanan #{order_id} | {qty} {item} ke {supplier}", "Agen AI", "system")

    return order_id, token

def get_orders(limit=10):
    """Ambil sejumlah pesanan terbaru."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM orders ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_order_by_id(order_id):
    """Ambil detail pesanan berdasarkan ID."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE id=?", (order_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0], "item": row[1], "qty": row[2], "supplier": row[3],
            "timestamp": row[4], "status": row[5], "confirm_token": row[6],
            "confirmed_at": row[7], "confirmed_by": row[8], "supplier_note": row[9]
        }
    return None

def get_order_by_token(token):
    """Ambil pesanan berdasarkan token konfirmasi."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE confirm_token=?", (token,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0], "item": row[1], "qty": row[2], "supplier": row[3],
            "timestamp": row[4], "status": row[5], "confirm_token": row[6],
            "confirmed_at": row[7], "confirmed_by": row[8], "supplier_note": row[9]
        }
    return None

def confirm_order(order_id):
    """Ubah status pesanan menjadi 'dikonfirmasi' (legacy)."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE orders SET status=?, confirmed_at=? WHERE id=?",
              ("dikonfirmasi", datetime.now().isoformat(), order_id))
    conn.commit()
    conn.close()

def confirm_order_by_token(token, supplier_name="Supplier", note=""):
    """
    Konfirmasi pesanan menggunakan token unik (dari email).
    Return: (success: bool, order_info: dict or error_msg: str)
    """
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Cari pesanan dengan token ini
    c.execute("SELECT id, item, qty, supplier, status FROM orders WHERE confirm_token=?", (token,))
    row = c.fetchone()

    if not row:
        conn.close()
        return False, "Token tidak valid atau pesanan tidak ditemukan."

    order_id, item, qty, supplier, status = row

    if status == "dikonfirmasi":
        conn.close()
        return False, f"Pesanan #{order_id} sudah dikonfirmasi sebelumnya."

    if status == "ditolak":
        conn.close()
        return False, f"Pesanan #{order_id} sudah ditolak sebelumnya."

    # Konfirmasi pesanan
    now = datetime.now().isoformat()
    c.execute(
        "UPDATE orders SET status=?, confirmed_at=?, confirmed_by=?, supplier_note=? WHERE confirm_token=?",
        ("dikonfirmasi", now, supplier_name, note, token)
    )
    conn.commit()
    conn.close()

    # Log aktivitas
    log_activity(
        "CONFIRM_ORDER",
        f"Pesanan #{order_id} dikonfirmasi oleh {supplier_name} via email",
        supplier_name, "supplier"
    )

    return True, {
        "order_id": order_id, "item": item, "qty": qty,
        "supplier": supplier, "confirmed_at": now
    }

def reject_order_by_token(token, supplier_name="Supplier", reason=""):
    """
    Tolak pesanan menggunakan token unik (dari email).
    Return: (success: bool, order_info: dict or error_msg: str)
    """
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT id, item, qty, supplier, status FROM orders WHERE confirm_token=?", (token,))
    row = c.fetchone()

    if not row:
        conn.close()
        return False, "Token tidak valid atau pesanan tidak ditemukan."

    order_id, item, qty, supplier, status = row

    if status != "dipesan":
        conn.close()
        return False, f"Pesanan #{order_id} sudah diproses (status: {status})."

    now = datetime.now().isoformat()
    c.execute(
        "UPDATE orders SET status=?, confirmed_at=?, confirmed_by=?, supplier_note=? WHERE confirm_token=?",
        ("ditolak", now, supplier_name, reason, token)
    )
    conn.commit()
    conn.close()

    log_activity(
        "REJECT_ORDER",
        f"Pesanan #{order_id} ditolak oleh {supplier_name}: {reason}",
        supplier_name, "supplier"
    )

    return True, {
        "order_id": order_id, "item": item, "qty": qty,
        "supplier": supplier, "rejected_at": now, "reason": reason
    }

def get_pending_orders():
    """Ambil semua pesanan yang belum dikonfirmasi."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE status='dipesan' ORDER BY timestamp DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def timeout_order(order_id):
    """Tandai pesanan sebagai timeout karena tidak ada konfirmasi."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE orders SET status=? WHERE id=?", ("timeout", order_id))
    conn.commit()
    conn.close()
    log_activity("TIMEOUT_ORDER", f"Pesanan #{order_id} timeout karena tidak dikonfirmasi", "System", "system")


# ============================================================
# FUNGSI SUPPLIER
# ============================================================
def get_supplier(name):
    """Ambil data supplier berdasarkan nama."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM suppliers WHERE name=?", (name,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"id": row[0], "name": row[1], "email": row[2], "phone": row[3], "address": row[4]}
    return None

def get_all_suppliers():
    """Ambil semua supplier aktif."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM suppliers WHERE is_active=1")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "email": r[2], "phone": r[3], "address": r[4]} for r in rows]

def update_supplier_email(name, new_email):
    """Perbarui email supplier."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE suppliers SET email=? WHERE name=?", (new_email, name))
    conn.commit()
    conn.close()


# ============================================================
# FUNGSI LOG AKTIVITAS
# ============================================================
def log_activity(action, detail, actor="System", role="system"):
    """Catat aktivitas ke log."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "INSERT INTO activity_log (action, detail, actor, role) VALUES (?,?,?,?)",
        (action, detail, actor, role)
    )
    conn.commit()
    conn.close()

def get_activity_log(limit=50):
    """Ambil log aktivitas terbaru."""
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


# ============================================================
# FUNGSI FASE MAGGOT (MONITORING SIKLUS HIDUP)
# ============================================================
def get_fase():
    """
    Ambil data fase terbaru (satu record terakhir).
    Mengembalikan dictionary agar mudah diakses, atau None jika kosong.
    """
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM fase_data ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "nama": row[1],
            "progress": row[2],
            "deskripsi": row[3],
            "suhu": row[4],
            "kelembaban": row[5],
            "cahaya": bool(row[6])
        }
    return None

def update_fase(nama, progress, deskripsi=""):
    """
    Ganti fase saat ini dengan data baru.
    Karena kita hanya menyimpan satu baris fase aktif, 
    fungsi ini menghapus data lama lalu memasukkan yang baru.
    """
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Ambil data lingkungan terakhir (jika ada) agar tetap tersimpan
    c.execute("SELECT suhu, kelembaban, cahaya FROM fase_data ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    if row:
        suhu, kelembaban, cahaya = row
    else:
        suhu, kelembaban, cahaya = 29.0, 75.0, 1

    # Hapus semua data fase (karena kita hanya butuh satu baris aktif)
    c.execute("DELETE FROM fase_data")
    # Masukkan data fase baru
    c.execute('''INSERT INTO fase_data 
                 (nama, progress, deskripsi, suhu, kelembaban, cahaya) 
                 VALUES (?,?,?,?,?,?)''',
              (nama, progress, deskripsi, suhu, kelembaban, cahaya))
    conn.commit()
    conn.close()

def update_env_data(suhu, kelembaban, cahaya):
    """
    Perbarui data lingkungan (suhu, kelembaban, cahaya) 
    pada record fase yang sedang aktif.
    """
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''UPDATE fase_data 
                 SET suhu=?, kelembaban=?, cahaya=?
                 WHERE id = (SELECT MAX(id) FROM fase_data)''',
              (suhu, kelembaban, int(cahaya)))
    conn.commit()
    conn.close()

def get_all_fase_data():
    """
    Ambil semua data fase (jika diperlukan untuk log/riwayat).
    """
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM fase_data ORDER BY id")
    rows = c.fetchall()
    conn.close()
    return rows