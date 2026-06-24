import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import socket

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "465").strip())
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "").strip()
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "").strip()
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "").strip()

def get_configured_email():
    """Ambil email penerima dari database (real-time), fallback ke .env."""
    try:
        from db import get_supplier
        supplier_info = get_supplier("Supplier A")
        if supplier_info and supplier_info.get("email"):
            email = supplier_info["email"]
            print(f"[EMAIL-CONFIG] Menggunakan email dari database: {email}")
            return email
    except Exception as e:
        print(f"[EMAIL-CONFIG] Gagal baca database: {e}")
    print(f"[EMAIL-CONFIG] Fallback ke .env: {EMAIL_RECEIVER}")
    return EMAIL_RECEIVER

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

# Base URL untuk konfirmasi (Flask server) - Gunakan IP Lokal agar bisa diakses dari HP/device lain
env_url = os.getenv("CONFIRM_BASE_URL")
if env_url:
    CONFIRM_BASE_URL = env_url
else:
    CONFIRM_BASE_URL = f"http://{get_local_ip()}:5050"


def send_email(subject, body, to_email=None):
    """Kirim notifikasi via email (plain text)."""
    recipient = to_email or get_configured_email() or ""
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = recipient
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, recipient, msg.as_string())
        print(f"[EMAIL] Terkirim ke {recipient}: {subject}")
        return True
    except Exception as e:
        print(f"[EMAIL] Gagal kirim ke {recipient}: {e}")
        return False


def send_order_email_to_supplier(order_id, token, item, qty, supplier_name, supplier_email=None):
    """
    Kirim email pesanan ke supplier dengan tombol konfirmasi & tolak.
    Supplier bisa langsung konfirmasi atau tolak dari email.
    """
    recipient = supplier_email or get_configured_email() or ""
    print(f"[EMAIL] Pesanan #{order_id} akan dikirim ke: {recipient}")
    confirm_url = f"{CONFIRM_BASE_URL}/confirm/{token}"
    reject_url = f"{CONFIRM_BASE_URL}/reject/{token}"
    detail_url = f"{CONFIRM_BASE_URL}/order/{token}"

    # Buat email HTML yang premium
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0; padding:0; background-color:#0f172a; font-family:'Segoe UI',Roboto,Arial,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0f172a; padding:40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background:linear-gradient(145deg,#1e293b,#0f172a); border-radius:16px; border:1px solid #334155; overflow:hidden;">
                        
                        <!-- Header -->
                        <tr>
                            <td style="background:linear-gradient(135deg,#3b82f6,#8b5cf6); padding:30px 40px; text-align:center;">
                                <h1 style="margin:0; color:#ffffff; font-size:24px; letter-spacing:1px;">
                                    📦 PESANAN BARU
                                </h1>
                                <p style="margin:8px 0 0; color:#e0e7ff; font-size:14px;">
                                    Sistem Agentic AI TPS 3R
                                </p>
                            </td>
                        </tr>

                        <!-- Body -->
                        <tr>
                            <td style="padding:32px 40px;">
                                <p style="color:#94a3b8; font-size:14px; margin:0 0 24px;">
                                    Halo <strong style="color:#f1f5f9;">{supplier_name}</strong>,<br>
                                    Sistem AI telah membuat pesanan baru yang memerlukan konfirmasi Anda.
                                </p>

                                <!-- Order Details Card -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="background:#1e293b; border:1px solid #334155; border-radius:12px; overflow:hidden; margin-bottom:24px;">
                                    <tr>
                                        <td style="padding:20px 24px; border-bottom:1px solid #334155;">
                                            <span style="color:#64748b; font-size:12px; text-transform:uppercase; letter-spacing:1px;">Order ID</span>
                                            <p style="margin:4px 0 0; color:#f1f5f9; font-size:20px; font-weight:bold;">#{order_id}</p>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding:16px 24px;">
                                            <table width="100%" cellpadding="0" cellspacing="0">
                                                <tr>
                                                    <td width="50%" style="padding:8px 0;">
                                                        <span style="color:#64748b; font-size:12px;">Item</span>
                                                        <p style="margin:4px 0 0; color:#e2e8f0; font-size:16px;">{item}</p>
                                                    </td>
                                                    <td width="50%" style="padding:8px 0;">
                                                        <span style="color:#64748b; font-size:12px;">Jumlah</span>
                                                        <p style="margin:4px 0 0; color:#fbbf24; font-size:16px; font-weight:bold;">{qty} gram</p>
                                                    </td>
                                                </tr>
                                                <tr>
                                                    <td width="50%" style="padding:8px 0;">
                                                        <span style="color:#64748b; font-size:12px;">Supplier</span>
                                                        <p style="margin:4px 0 0; color:#e2e8f0; font-size:16px;">{supplier_name}</p>
                                                    </td>
                                                    <td width="50%" style="padding:8px 0;">
                                                        <span style="color:#64748b; font-size:12px;">Status</span>
                                                        <p style="margin:4px 0 0;">
                                                            <span style="background:#fbbf24; color:#0f172a; padding:2px 10px; border-radius:999px; font-size:12px; font-weight:bold;">
                                                                Menunggu Konfirmasi
                                                            </span>
                                                        </p>
                                                    </td>
                                                </tr>
                                            </table>
                                        </td>
                                    </tr>
                                </table>

                                <!-- Alert -->
                                <table width="100%" cellpadding="0" cellspacing="0" style="background:rgba(251,191,36,0.1); border:1px solid rgba(251,191,36,0.3); border-radius:8px; margin-bottom:28px;">
                                    <tr>
                                        <td style="padding:14px 20px;">
                                            <p style="margin:0; color:#fbbf24; font-size:13px;">
                                                ⚠️ Pesanan ini dibuat otomatis karena stok starter maggot telah mencapai ambang batas minimum.
                                            </p>
                                        </td>
                                    </tr>
                                </table>

                                <!-- CTA Buttons -->
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center" style="padding-bottom:12px;">
                                            <a href="{confirm_url}" style="display:inline-block; background:linear-gradient(135deg,#22c55e,#16a34a); color:#ffffff; text-decoration:none; padding:14px 48px; border-radius:8px; font-size:16px; font-weight:bold; letter-spacing:0.5px;">
                                                ✅ KONFIRMASI PESANAN
                                            </a>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="center" style="padding-bottom:12px;">
                                            <a href="{reject_url}" style="display:inline-block; background:linear-gradient(135deg,#ef4444,#dc2626); color:#ffffff; text-decoration:none; padding:14px 48px; border-radius:8px; font-size:16px; font-weight:bold; letter-spacing:0.5px;">
                                                ❌ TOLAK PESANAN
                                            </a>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td align="center">
                                            <a href="{detail_url}" style="color:#60a5fa; text-decoration:none; font-size:13px;">
                                                Lihat Detail Pesanan →
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="padding:20px 40px; border-top:1px solid #334155; text-align:center;">
                                <p style="margin:0; color:#475569; font-size:11px;">
                                    Email ini dikirim otomatis oleh Sistem Agentic AI TPS 3R.<br>
                                    Klik tombol di atas untuk mengonfirmasi atau menolak pesanan.
                                </p>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    # Buat email multipart (HTML + plain text fallback)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📦 PESANAN BARU #{order_id} - Konfirmasi Diperlukan"
    msg["From"] = EMAIL_SENDER
    msg["To"] = recipient

    # Plain text fallback
    plain_body = (
        f"PESANAN BARU #{order_id}\n"
        f"{'='*40}\n"
        f"Item: {item}\n"
        f"Jumlah: {qty} gram\n"
        f"Supplier: {supplier_name}\n"
        f"Status: Menunggu Konfirmasi\n\n"
        f"Untuk KONFIRMASI pesanan, buka link berikut:\n{confirm_url}\n\n"
        f"Untuk MENOLAK pesanan, buka link berikut:\n{reject_url}\n\n"
        f"Lihat detail: {detail_url}\n\n"
        f"---\nEmail ini dikirim otomatis oleh Sistem Agentic AI TPS 3R."
    )

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, recipient, msg.as_string())
        print(f"[EMAIL] Pesanan #{order_id} terkirim ke {recipient}")
        return True
    except Exception as e:
        print(f"[EMAIL] Gagal kirim pesanan #{order_id}: {e}")
        return False


def send_confirmation_notification(order_id, item, qty, supplier_name, action="dikonfirmasi"):
    """Kirim notifikasi bahwa pesanan telah dikonfirmasi/ditolak ke admin."""
    color = "#22c55e" if action == "dikonfirmasi" else "#ef4444"
    icon = "✅" if action == "dikonfirmasi" else "❌"
    
    subject = f"{icon} Pesanan #{order_id} {action.upper()} oleh {supplier_name}"
    body = (
        f"Pesanan #{order_id} untuk {item} sebanyak {qty} gram\n"
        f"telah {action} oleh {supplier_name}.\n\n"
        f"Status pesanan telah diperbarui di sistem.\n\n"
        f"---\nSistem Agentic AI TPS 3R"
    )
    return send_email(subject, body)