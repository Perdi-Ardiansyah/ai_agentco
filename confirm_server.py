"""
Flask server untuk konfirmasi pesanan via email.
Supplier klik link di email → halaman konfirmasi di browser.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)  # pyrefly: ignore[missing-attribute]

import threading
import time
from flask import Flask, request, render_template_string
from db import (get_order_by_token, confirm_order_by_token,
                reject_order_by_token, update_stock, get_stock, log_activity)
from notifier import send_confirmation_notification

app = Flask(__name__)

# ============ HTML TEMPLATES ============

BASE_CSS = """
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:'Segoe UI',Roboto,sans-serif; background:#0f172a; color:#e2e8f0; min-height:100vh; display:flex; align-items:center; justify-content:center; padding:20px; }
  .card { background:linear-gradient(145deg,#1e293b,#0f172a); border:1px solid #334155; border-radius:16px; max-width:520px; width:100%; overflow:hidden; }
  .header { padding:28px 32px; text-align:center; }
  .header h1 { font-size:22px; margin-bottom:6px; }
  .header p { color:#94a3b8; font-size:13px; }
  .body { padding:24px 32px; }
  .info-row { display:flex; justify-content:space-between; padding:10px 0; border-bottom:1px solid #1e293b; }
  .info-label { color:#64748b; font-size:13px; }
  .info-value { color:#f1f5f9; font-weight:600; }
  .badge { display:inline-block; padding:3px 12px; border-radius:999px; font-size:12px; font-weight:700; }
  .badge-warn { background:#fbbf24; color:#0f172a; }
  .badge-ok { background:#22c55e; color:#fff; }
  .badge-err { background:#ef4444; color:#fff; }
  .btn { display:block; width:100%; padding:14px; border:none; border-radius:8px; font-size:15px; font-weight:700; cursor:pointer; margin-top:10px; text-decoration:none; text-align:center; color:#fff; }
  .btn-confirm { background:linear-gradient(135deg,#22c55e,#16a34a); }
  .btn-reject { background:linear-gradient(135deg,#ef4444,#dc2626); }
  .btn:hover { opacity:.9; }
  textarea { width:100%; background:#0f172a; border:1px solid #334155; border-radius:8px; color:#e2e8f0; padding:10px; margin-top:8px; resize:vertical; min-height:60px; font-family:inherit; }
  .footer { padding:16px 32px; border-top:1px solid #1e293b; text-align:center; }
  .footer p { color:#475569; font-size:11px; }
  .msg { padding:20px 32px; text-align:center; }
  .msg h2 { font-size:48px; margin-bottom:12px; }
</style>
"""

DETAIL_PAGE = BASE_CSS + """
<div class="card">
  <div class="header" style="background:linear-gradient(135deg,#3b82f6,#8b5cf6);">
    <h1>📦 Detail Pesanan #{{o.id}}</h1>
    <p>Sistem Agentic AI TPS 3R</p>
  </div>
  <div class="body">
    <div class="info-row"><span class="info-label">Item</span><span class="info-value">{{o.item}}</span></div>
    <div class="info-row"><span class="info-label">Jumlah</span><span class="info-value">{{o.qty}} gram</span></div>
    <div class="info-row"><span class="info-label">Supplier</span><span class="info-value">{{o.supplier}}</span></div>
    <div class="info-row"><span class="info-label">Waktu</span><span class="info-value">{{o.timestamp}}</span></div>
    <div class="info-row"><span class="info-label">Status</span><span class="info-value">
      {% if o.status == 'dipesan' %}<span class="badge badge-warn">Menunggu</span>
      {% elif o.status == 'dikonfirmasi' %}<span class="badge badge-ok">Dikonfirmasi</span>
      {% elif o.status == 'timeout' %}<span class="badge" style="background:#64748b; color:#fff;">Timeout / Kadaluarsa</span>
      {% else %}<span class="badge badge-err">Ditolak</span>{% endif %}
    </span></div>
    {% if o.confirmed_by %}
    <div class="info-row"><span class="info-label">Dikonfirmasi oleh</span><span class="info-value">{{o.confirmed_by}}</span></div>
    {% endif %}
    {% if o.status == 'dipesan' %}
    <div style="margin-top:20px;">
      <a href="/confirm/{{o.confirm_token}}" class="btn btn-confirm">✅ Konfirmasi Pesanan</a>
      <a href="/reject/{{o.confirm_token}}" class="btn btn-reject">❌ Tolak Pesanan</a>
    </div>
    {% endif %}
  </div>
  <div class="footer"><p>Agentic AI TPS 3R</p></div>
</div>
"""

CONFIRM_PAGE = BASE_CSS + """
<div class="card">
  <div class="header" style="background:linear-gradient(135deg,#22c55e,#16a34a);">
    <h1>✅ Konfirmasi Pesanan #{{o.id}}</h1>
    <p>Konfirmasi sebagai supplier</p>
  </div>
  <div class="body">
    <div class="info-row"><span class="info-label">Item</span><span class="info-value">{{o.item}}</span></div>
    <div class="info-row"><span class="info-label">Jumlah</span><span class="info-value">{{o.qty}} gram</span></div>
    <div class="info-row"><span class="info-label">Supplier</span><span class="info-value">{{o.supplier}}</span></div>
    <form method="POST" style="margin-top:16px;">
      <label class="info-label">Catatan (opsional):</label>
      <textarea name="note" placeholder="Contoh: Barang akan dikirim besok pagi..."></textarea>
      <button type="submit" class="btn btn-confirm">✅ KONFIRMASI SEKARANG</button>
    </form>
    <a href="/order/{{o.confirm_token}}" style="display:block;text-align:center;color:#60a5fa;margin-top:12px;font-size:13px;">← Kembali ke Detail</a>
  </div>
</div>
"""

REJECT_PAGE = BASE_CSS + """
<div class="card">
  <div class="header" style="background:linear-gradient(135deg,#ef4444,#dc2626);">
    <h1>❌ Tolak Pesanan #{{o.id}}</h1>
    <p>Berikan alasan penolakan</p>
  </div>
  <div class="body">
    <div class="info-row"><span class="info-label">Item</span><span class="info-value">{{o.item}}</span></div>
    <div class="info-row"><span class="info-label">Jumlah</span><span class="info-value">{{o.qty}} gram</span></div>
    <form method="POST" style="margin-top:16px;">
      <label class="info-label">Alasan penolakan:</label>
      <textarea name="reason" placeholder="Contoh: Stok supplier habis..." required></textarea>
      <button type="submit" class="btn btn-reject">❌ TOLAK PESANAN</button>
    </form>
    <a href="/order/{{o.confirm_token}}" style="display:block;text-align:center;color:#60a5fa;margin-top:12px;font-size:13px;">← Kembali ke Detail</a>
  </div>
</div>
"""

RESULT_PAGE = BASE_CSS + """
<div class="card">
  <div class="msg">
    <h2>{{icon}}</h2>
    <h1 style="color:{{color}};margin-bottom:8px;">{{title}}</h1>
    <p style="color:#94a3b8;">{{message}}</p>
  </div>
  <div class="footer"><p>Agentic AI TPS 3R</p></div>
</div>
"""

# ============ ROUTES ============

@app.route("/order/<token>")
def order_detail(token):
    o = get_order_by_token(token)
    if not o:
        return render_template_string(RESULT_PAGE, icon="❓", color="#ef4444",
                                      title="Tidak Ditemukan", message="Token pesanan tidak valid.")
    return render_template_string(DETAIL_PAGE, o=o)


@app.route("/confirm/<token>", methods=["GET", "POST"])
def confirm_page(token):
    o = get_order_by_token(token)
    if not o:
        return render_template_string(RESULT_PAGE, icon="❓", color="#ef4444",
                                      title="Tidak Ditemukan", message="Token tidak valid.")

    if o["status"] != "dipesan":
        return render_template_string(RESULT_PAGE, icon="ℹ️", color="#3b82f6",
                                      title="Sudah Diproses", message=f"Pesanan #{o['id']} status: {o['status']}")

    if request.method == "POST":
        note = request.form.get("note", "")
        success, info = confirm_order_by_token(token, o["supplier"], note)
        if success:
            # Simulasi pengiriman stok setelah dikonfirmasi supplier
            def delayed_restock():
                time.sleep(30)
                current, _, _ = get_stock(o["item"])
                update_stock(o["item"], current + o["qty"])
                log_activity("RESTOCK", f"+{o['qty']} {o['item']} diterima dari {o['supplier']}", "System", "system")
                print(f"📦 Stok +{o['qty']}g dari {o['supplier']}")
            threading.Thread(target=delayed_restock, daemon=True).start()

            send_confirmation_notification(o["id"], o["item"], o["qty"], o["supplier"], "dikonfirmasi")
            return render_template_string(RESULT_PAGE, icon="✅", color="#22c55e",
                                          title="Pesanan Dikonfirmasi!",
                                          message=f"Pesanan #{o['id']} ({o['qty']}g {o['item']}) akan segera dikirim.")
        return render_template_string(RESULT_PAGE, icon="⚠️", color="#fbbf24",
                                      title="Gagal", message=str(info))

    return render_template_string(CONFIRM_PAGE, o=o)


@app.route("/reject/<token>", methods=["GET", "POST"])
def reject_page(token):
    o = get_order_by_token(token)
    if not o:
        return render_template_string(RESULT_PAGE, icon="❓", color="#ef4444",
                                      title="Tidak Ditemukan", message="Token tidak valid.")

    if o["status"] != "dipesan":
        return render_template_string(RESULT_PAGE, icon="ℹ️", color="#3b82f6",
                                      title="Sudah Diproses", message=f"Pesanan #{o['id']} status: {o['status']}")

    if request.method == "POST":
        reason = request.form.get("reason", "Tidak ada alasan")
        success, info = reject_order_by_token(token, o["supplier"], reason)
        if success:
            send_confirmation_notification(o["id"], o["item"], o["qty"], o["supplier"], "ditolak")
            return render_template_string(RESULT_PAGE, icon="❌", color="#ef4444",
                                          title="Pesanan Ditolak",
                                          message=f"Pesanan #{o['id']} ditolak. Alasan: {reason}")
        return render_template_string(RESULT_PAGE, icon="⚠️", color="#fbbf24",
                                      title="Gagal", message=str(info))

    return render_template_string(REJECT_PAGE, o=o)


@app.route("/")
def index():
    return render_template_string(RESULT_PAGE, icon="📦", color="#3b82f6",
                                  title="TPS 3R Order System",
                                  message="Gunakan link dari email untuk konfirmasi pesanan.")


def run_confirm_server():
    """Jalankan Flask server di background thread."""
    print("🌐 Confirm Server berjalan di http://localhost:5050")
    app.run(host="0.0.0.0", port=5050, debug=False, use_reloader=False)


if __name__ == "__main__":
    run_confirm_server()
