import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go  # pyrefly: ignore[missing-import]
from datetime import datetime
import threading
import time
from db import get_pending_orders, get_activity_log, get_supplier, update_supplier_email
from fase_sim import FASE_CONFIG
from confirm_server import run_confirm_server

st.set_page_config(page_title="TPS 3R · Smart Dashboard", layout="wide")

@st.cache_resource
def start_background_server():
    server_thread = threading.Thread(target=run_confirm_server, daemon=True)
    server_thread.start()
    time.sleep(1)
    return True

start_background_server()

# ===================== GLOBAL CSS =====================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
h1, h2, h3, h4, h5, h6, p, a, label, li, .stMarkdown, .stMetric, [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { font-family: 'Inter', sans-serif !important; }
.material-symbols-rounded, .material-icons, i, [class*="icon"] { font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important; }
.stApp { background: #060918; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0c1029 0%, #0a0e24 100%); border-right: 1px solid rgba(99,102,241,0.15); }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: #c7d2fe !important; }
.block-container { padding: 1.5rem 2rem 2rem; max-width: 1400px; }
h1 { color: #f1f5f9 !important; font-weight: 800 !important; letter-spacing: -0.5px !important; }
h2, h3 { color: #e2e8f0 !important; font-weight: 600 !important; }
p, span, label, li { color: #cbd5e1 !important; }
[data-testid="stTabs"] button { color: #94a3b8 !important; font-weight: 600 !important; border-radius: 8px 8px 0 0 !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color: #c7d2fe !important; border-bottom: 2px solid #818cf8 !important; background: rgba(99,102,241,0.08) !important; }
.stButton > button { background: rgba(30,41,59, 0.8) !important; color: #f8fafc !important; border: 1px solid rgba(99,102,241,0.3) !important; border-radius: 8px !important; font-weight: 600 !important; transition: all 0.2s !important; }
.stButton > button:hover { background: rgba(99,102,241, 0.2) !important; border-color: rgba(99,102,241, 0.8) !important; color: #ffffff !important; box-shadow: 0 4px 12px rgba(99,102,241,0.2) !important; }
.stButton > button * { color: inherit !important; }
.metric-card { background: linear-gradient(135deg, rgba(15,23,42,0.9), rgba(30,41,59,0.7)); backdrop-filter: blur(20px); border: 1px solid rgba(99,102,241,0.2); border-radius: 16px; padding: 24px; position: relative; overflow: hidden; }
.metric-card::before { content:''; position:absolute; top:0; left:0; right:0; height:3px; border-radius:16px 16px 0 0; }
.metric-card .label { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 8px; }
.metric-card .value { font-size: 32px; font-weight: 800; color: #f1f5f9 !important; line-height: 1.1; }
.metric-card .sub { font-size: 12px; color: #64748b !important; margin-top: 6px; }
.mc-blue::before { background: linear-gradient(90deg, #3b82f6, #6366f1); }
.mc-green::before { background: linear-gradient(90deg, #10b981, #34d399); }
.mc-amber::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.mc-purple::before { background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
.mc-rose::before { background: linear-gradient(90deg, #f43f5e, #fb7185); }
.mc-cyan::before { background: linear-gradient(90deg, #06b6d4, #22d3ee); }
.order-card { background: rgba(15,23,42,0.8); border: 1px solid rgba(51,65,85,0.5); border-radius: 12px; padding: 16px 20px; margin-bottom: 10px; transition: all 0.2s; }
.order-card:hover { border-color: rgba(99,102,241,0.4); transform: translateX(4px); }
.badge { display:inline-block; padding:3px 10px; border-radius:6px; font-size:11px; font-weight:700; letter-spacing:0.5px; }
.b-pending { background:rgba(251,191,36,0.15); color:#fbbf24 !important; border:1px solid rgba(251,191,36,0.3); }
.b-confirmed { background:rgba(34,197,94,0.15); color:#22c55e !important; border:1px solid rgba(34,197,94,0.3); }
.b-rejected { background:rgba(239,68,68,0.15); color:#ef4444 !important; border:1px solid rgba(239,68,68,0.3); }
.log-item { background: rgba(15,23,42,0.6); border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; border-left: 3px solid; }
.flow-step { display:flex; align-items:center; gap:12px; padding:12px 0; border-bottom:1px solid rgba(51,65,85,0.3); }
.flow-num { width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700; flex-shrink:0; }
.section-divider { height:1px; background:linear-gradient(90deg,transparent,rgba(99,102,241,0.3),transparent); margin:24px 0; }
@keyframes pulse-dot { 0%,100% { opacity:1; } 50% { opacity:0.3; } }
</style>
""", unsafe_allow_html=True)

conn = sqlite3.connect("tps.db")

# ===================== SIDEBAR =====================
with st.sidebar:
    import os
    if os.path.exists("Logo AI Agent.png"):
        col1, col2, col3 = st.columns([1, 4, 1])
        with col2:
            st.image("Logo AI Agent.png", use_container_width=True)
    else:
        st.markdown("""
        <div style="text-align:center; padding:20px 0 10px;">
            <div style="font-size:42px; margin-bottom:4px;" class="material-symbols-rounded">biotech</div>
            <h2 style="margin:0; font-size:20px; font-weight:800; background:linear-gradient(135deg,#818cf8,#6366f1);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">TPS 3R</h2>
            <p style="margin:4px 0 0; font-size:11px; color:#64748b !important; letter-spacing:2px; text-transform:uppercase;">Smart Operations</p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # System status
    st.markdown("##### System Status")
    st.markdown("""
    <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.2); border-radius:10px; padding:12px 14px; margin-bottom:8px;">
        <span style="color:#10b981 !important; font-weight:600;">● Agent AI</span><span style="float:right; color:#10b981 !important; font-size:12px;">Online</span>
    </div>
    <div style="background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.2); border-radius:10px; padding:12px 14px; margin-bottom:8px;">
        <span style="color:#818cf8 !important; font-weight:600;">● Confirm Server</span><span style="float:right; color:#818cf8 !important; font-size:12px;">:5050</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    # Pending count
    pending = get_pending_orders()
    pending_count = len(pending) if pending else 0
    pcolor = "#fbbf24" if pending_count > 0 else "#10b981"
    st.markdown(f"""
    <div style="background:rgba(30,41,59,0.5); border-radius:10px; padding:14px; text-align:center;">
        <div style="font-size:28px; font-weight:800; color:{pcolor} !important;">{pending_count}</div>
        <div style="font-size:11px; color:#64748b !important; text-transform:uppercase; letter-spacing:1px;">Menunggu Konfirmasi</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    now = datetime.now().strftime("%d %b %Y, %H:%M")
    st.markdown(f'<p style="text-align:center; font-size:11px; color:#475569 !important;">Last refresh: {now}</p>', unsafe_allow_html=True)

    if st.button("Refresh Data", use_container_width=True):
        st.rerun()

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
    st.markdown("##### Email Penerima")
    st.markdown("<p style='font-size:12px; color:#94a3b8 !important;'>Email ini akan menerima notifikasi pesanan dan link konfirmasi.</p>", unsafe_allow_html=True)
    
    supplier_info = get_supplier("Supplier A")
    current_email = supplier_info["email"] if supplier_info else ""
    
    # Tampilkan email aktif saat ini
    st.markdown(f"""
    <div style="background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.2); border-radius:8px; padding:10px 14px; margin-bottom:10px;">
        <span style="color:#64748b !important; font-size:10px; text-transform:uppercase; letter-spacing:1px;">Email Aktif</span><br>
        <span style="color:#a5b4fc !important; font-size:13px; font-weight:600; word-break:break-all;">{current_email or 'Belum dikonfigurasi'}</span>
    </div>
    """, unsafe_allow_html=True)
    
    new_email = st.text_input("Alamat Email:", value=current_email, key="sidebar_email_input", label_visibility="collapsed")
    
    col_save, col_test = st.columns(2)
    with col_save:
        if st.button("Simpan", use_container_width=True):
            if new_email and "@" in new_email:
                update_supplier_email("Supplier A", new_email)
                st.success("Tersimpan!")
                st.rerun()
            else:
                st.error("Format email tidak valid.")
    with col_test:
        if st.button("Test", use_container_width=True):
            from notifier import get_configured_email, SMTP_SERVER, SMTP_PORT, EMAIL_SENDER, EMAIL_PASSWORD
            import smtplib
            from email.mime.text import MIMEText as _MT
            target = get_configured_email()
            st.info(f"Mengirim ke: {target}")
            try:
                msg = _MT(
                    f"Ini adalah email test dari sistem TPS 3R.\n\n"
                    f"Email ini dikirim ke: {target}\n"
                    f"Jika Anda menerima email ini, berarti konfigurasi email sudah benar.\n\n"
                    f"---\nSistem Agentic AI TPS 3R",
                    "plain", "utf-8"
                )
                msg["Subject"] = "Test Email - TPS 3R"
                msg["From"] = EMAIL_SENDER
                msg["To"] = target
                with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                    server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                    server.sendmail(EMAIL_SENDER, target, msg.as_string())
                st.success(f"Terkirim ke {target}!")
            except Exception as e:
                st.error(f"Gagal: {e}")

# ===================== HEADER =====================
st.markdown("""
<div style="margin-bottom:8px;">
    <h1 style="margin:0; font-size:28px;">Smart Operations Dashboard</h1>
    <p style="margin:4px 0 0; font-size:13px; color:#64748b !important;">Automated supply chain monitoring · Supplier confirms via email</p>
</div>
""", unsafe_allow_html=True)

# ===================== TABS =====================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Overview", "Order History", "Supplier Flow", "Activity Log", "Simulasi Agent"])

# ==================== TAB 1: OVERVIEW ====================
with tab1:
    df_stock = pd.read_sql_query("SELECT * FROM inventory", conn)
    fase = pd.read_sql_query("SELECT * FROM fase_data ORDER BY id DESC LIMIT 1", conn)
    order_stats = pd.read_sql_query("SELECT status, COUNT(*) as cnt FROM orders GROUP BY status", conn)

    stock_val = float(df_stock.iloc[0]['stock']) if not df_stock.empty else 0
    thresh_val = float(df_stock.iloc[0]['threshold']) if not df_stock.empty else 50
    unit = df_stock.iloc[0]['unit'] if not df_stock.empty else "gram"
    stock_pct = min(stock_val / 200 * 100, 100)

    nama_fase = fase.iloc[0]['nama'] if not fase.empty else "N/A"
    progress = float(fase.iloc[0]['progress']) if not fase.empty else 0
    suhu = float(fase.iloc[0]['suhu']) if not fase.empty else 0
    kelembaban = float(fase.iloc[0]['kelembaban']) if not fase.empty else 0
    deskripsi = fase.iloc[0]['deskripsi'] if not fase.empty else ""

    confirmed = int(order_stats[order_stats['status']=='dikonfirmasi']['cnt'].sum()) if not order_stats.empty else 0
    pending_n = int(order_stats[order_stats['status']=='dipesan']['cnt'].sum()) if not order_stats.empty else 0
    total_orders = int(order_stats['cnt'].sum()) if not order_stats.empty else 0

    # ---- Metric Cards Row ----
    status_dot = '<span class="material-symbols-rounded" style="color:#ef4444; font-size:16px; vertical-align:middle;">error</span>' if stock_val <= thresh_val else '<span class="material-symbols-rounded" style="color:#22c55e; font-size:16px; vertical-align:middle;">check_circle</span>'
    fase_icon = {"telur":"egg","larva_muda":"bug_report","larva_dewasa":"bug_report","pre_pupa":"sync","pupa":"grain","lalat_dewasa":"pest_control"}.get(nama_fase,"science")
    fase_icon_html = f'<span class="material-symbols-rounded" style="font-size:16px; vertical-align:middle;">{fase_icon}</span>'
    
    st.markdown(f"""
    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:16px; margin-bottom:24px;">
        <div class="metric-card mc-blue">
            <div class="label" style="color:#60a5fa !important;">Stok Pakan {status_dot}</div>
            <div class="value">{stock_val:.0f}<span style="font-size:14px; color:#64748b !important;"> {unit}</span></div>
            <div class="sub">Threshold: {thresh_val:.0f} {unit}</div>
        </div>
        <div class="metric-card mc-purple">
            <div class="label" style="color:#a78bfa !important;">Fase Aktif {fase_icon_html}</div>
            <div class="value" style="font-size:24px;">{nama_fase.replace('_',' ').title()}</div>
            <div class="sub">Progress: {progress:.1f}%</div>
        </div>
        <div class="metric-card mc-green">
            <div class="label" style="color:#34d399 !important;">Total Pesanan</div>
            <div class="value">{total_orders}</div>
            <div class="sub">{confirmed} dikonfirmasi · {pending_n} pending</div>
        </div>
        <div class="metric-card mc-cyan">
            <div class="label" style="color:#22d3ee !important;">Lingkungan</div>
            <div class="value" style="font-size:22px; white-space:nowrap;">{suhu}°C · {kelembaban}%</div>
            <div class="sub">Suhu · Kelembaban</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ---- Charts Row ----
    col_gauge, col_phase = st.columns(2)

    with col_gauge:
        st.markdown("<h3 style='text-align:center; font-size:14px; color:#94a3b8; font-weight:600; margin-bottom:0;'>Level Stok Pakan</h3>", unsafe_allow_html=True)
        # Stock Gauge
        gauge_color = "#ef4444" if stock_val <= thresh_val else ("#fbbf24" if stock_val <= thresh_val*2 else "#22c55e")
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=stock_val,
            number={"suffix": f" {unit}", "font": {"size": 36, "color": "#f1f5f9"}},
            delta={"reference": thresh_val, "increasing": {"color": "#22c55e"}, "decreasing": {"color": "#ef4444"}},
            gauge={
                "axis": {"range": [0, 250], "tickcolor": "#334155", "tickfont": {"color": "#64748b"}},
                "bar": {"color": gauge_color, "thickness": 0.75},
                "bgcolor": "#1e293b",
                "bordercolor": "#334155",
                "steps": [
                    {"range": [0, thresh_val], "color": "rgba(239,68,68,0.12)"},
                    {"range": [thresh_val, thresh_val*2], "color": "rgba(251,191,36,0.08)"},
                    {"range": [thresh_val*2, 250], "color": "rgba(34,197,94,0.06)"}
                ],
                "threshold": {"line": {"color": "#fbbf24", "width": 3}, "thickness": 0.8, "value": thresh_val}
            }
        ))
        fig_gauge.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=250, margin=dict(t=20, b=10, l=30, r=30), font={"color": "#94a3b8"}
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    with col_phase:
        st.markdown("<h3 style='text-align:center; font-size:14px; color:#94a3b8; font-weight:600; margin-bottom:0;'>Progress Fase Maggot</h3>", unsafe_allow_html=True)
        # Phase Progress Donut
        fase_cfg = FASE_CONFIG.get(nama_fase)
        durasi = float(fase_cfg["durasi"]) if fase_cfg else 60.0  # pyrefly: ignore[bad-argument-type]
        sisa = durasi * (100 - progress) / 100
        fase_colors = {"telur":"#818cf8","larva_muda":"#34d399","larva_dewasa":"#22c55e","pre_pupa":"#fbbf24","pupa":"#f97316","lalat_dewasa":"#f43f5e"}
        fc = fase_colors.get(nama_fase, "#818cf8")

        fig_donut = go.Figure(go.Pie(
            values=[progress, 100-progress], hole=0.75,
            marker={"colors": [fc, "rgba(30,41,59,0.5)"], "line": {"width": 0}},
            textinfo="none", hoverinfo="skip", direction="clockwise", sort=False
        ))
        fig_donut.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=250, margin=dict(t=10, b=10, l=10, r=10), showlegend=False,
            annotations=[
                dict(
                    text=f"<span style='font-size:28px; color:#f1f5f9; font-weight:bold;'>{progress:.0f}%</span><br><span style='font-size:12px; color:#64748b;'>~{sisa:.0f}s tersisa</span>",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    align="center",
                    xanchor="center",
                    yanchor="middle"
                )
            ]
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    # ---- Fase Detail ----
    st.markdown(f"""
    <div style="background:rgba(15,23,42,0.8); border:1px solid rgba(99,102,241,0.15); border-radius:12px; padding:18px 22px; display:flex; gap:24px; align-items:center; flex-wrap:wrap; justify-content:space-between;">
        <div style="flex: 1; min-width: 250px;">
            <span style="color:#64748b !important; font-size:11px; text-transform:uppercase; letter-spacing:1px;">Deskripsi</span><br>
            <span style="color:#e2e8f0 !important; font-weight:500; font-size:15px;">{deskripsi}</span>
        </div>
        <div style="display:flex; gap:24px; flex-wrap:wrap;">
            <div style="text-align:center;"><span style="color:#64748b !important; font-size:11px;">🌡️ Suhu</span><br><span style="color:#f1f5f9 !important; font-weight:700;">{suhu}°C</span></div>
            <div style="text-align:center;"><span style="color:#64748b !important; font-size:11px;">💧 Lembab</span><br><span style="color:#f1f5f9 !important; font-weight:700;">{kelembaban}%</span></div>
            <div style="text-align:center;"><span style="color:#64748b !important; font-size:11px;">⏱️ Sisa</span><br><span style="color:#fbbf24 !important; font-weight:700;">{sisa:.0f}s</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==================== TAB 2: ORDER HISTORY ====================
with tab2:
    st.markdown('<p style="color:#64748b !important; font-size:13px; margin-bottom:16px;">Supplier mengonfirmasi pesanan langsung melalui link di email — bukan dari dashboard.</p>', unsafe_allow_html=True)

    df_orders = pd.read_sql_query(
        "SELECT id, item, qty, supplier, timestamp, status, confirmed_by, confirmed_at, supplier_note FROM orders ORDER BY timestamp DESC LIMIT 30", conn)

    if df_orders.empty:
        st.markdown("""
        <div style="text-align:center; padding:60px 0;">
            <div style="font-size:48px; margin-bottom:12px;">📭</div>
            <p style="color:#475569 !important; font-size:15px;">Belum ada pesanan tercatat</p>
        </div>""", unsafe_allow_html=True)
    else:
        for _, r in df_orders.iterrows():
            s = r['status']
            badge_cls = {"dipesan":"b-pending","dikonfirmasi":"b-confirmed","timeout":"b-rejected"}.get(s,"b-rejected")
            badge_txt = {"dipesan":"PENDING","dikonfirmasi":"CONFIRMED","timeout":"TIMEOUT"}.get(s,"REJECTED")
            bl_color = {"dipesan":"#fbbf24","dikonfirmasi":"#22c55e","timeout":"#94a3b8"}.get(s,"#ef4444")

            extra = ""
            c_by = r.get('confirmed_by')
            if pd.notna(c_by) and str(c_by).strip() and str(c_by).strip() not in ('None', 'nan'):
                extra += f'<span style="color:#64748b !important; font-size:11px; margin-left:12px;">oleh {c_by}</span>'
            s_note = r.get('supplier_note')
            if pd.notna(s_note) and str(s_note).strip() and str(s_note).strip() not in ('None', 'nan'):
                extra += f'<div style="margin-top:6px; padding:8px 12px; background:rgba(99,102,241,0.06); border-radius:6px; font-size:12px; color:#94a3b8 !important;">📝 {s_note}</div>'

            st.markdown(f"""
            <div class="order-card" style="border-left:3px solid {bl_color};">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                    <div>
                        <span style="color:#f1f5f9 !important; font-weight:700; font-size:15px;">#{r['id']}</span>
                        <span style="color:#64748b !important; margin:0 8px;">·</span>
                        <span style="color:#94a3b8 !important;">{r['item']}</span>
                        <span style="color:#64748b !important; margin:0 6px;">·</span>
                        <span style="color:#e2e8f0 !important; font-weight:600;">{r['qty']}g</span>
                        <span style="color:#64748b !important; margin:0 6px;">→</span>
                        <span style="color:#94a3b8 !important;">{r['supplier']}</span>{extra}
                    </div>
                    <div style="display:flex; align-items:center; gap:12px;">
                        <span style="color:#475569 !important; font-size:11px;">{r['timestamp']}</span>
                        <span class="badge {badge_cls}">{badge_txt}</span>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

# ==================== TAB 3: SUPPLIER FLOW ====================
with tab3:
    steps = [
        ("#f43f5e","1","Stok pakan turun di bawah threshold minimum"),
        ("#f59e0b","2","Agent AI otomatis membuat pesanan ke supplier"),
        ("#6366f1","3","Email HTML dikirim ke supplier dengan tombol aksi"),
        ("#22c55e","4","Supplier klik Konfirmasi atau Tolak di email"),
        ("#3b82f6","5","Status pesanan terupdate otomatis di sistem"),
    ]
    st.markdown("""
    <div style="background:rgba(15,23,42,0.8); border:1px solid rgba(99,102,241,0.15); border-radius:14px; padding:24px 28px; margin-bottom:20px;">
        <h3 style="margin:0 0 16px; font-size:16px; color:#e2e8f0 !important;">Alur Konfirmasi Pesanan</h3>
    """, unsafe_allow_html=True)
    for color, num, text in steps:
        st.markdown(f"""
        <div class="flow-step">
            <div class="flow-num" style="background:{color}; color:#fff !important;">{num}</div>
            <span style="color:#cbd5e1 !important; font-size:14px;">{text}</span>
        </div>""", unsafe_allow_html=True)
    st.markdown("""
        <div style="margin-top:16px; padding:12px 16px; background:rgba(99,102,241,0.08); border-radius:8px; border:1px solid rgba(99,102,241,0.2);">
            <span style="color:#818cf8 !important; font-size:13px;">🌐 Confirm Server aktif di <code style="color:#a5b4fc; background:rgba(99,102,241,0.15); padding:2px 8px; border-radius:4px;">localhost:5050</code></span>
        </div>
    </div>""", unsafe_allow_html=True)

    # Pending orders
    if pending_count > 0:
        st.markdown(f'<div style="background:rgba(251,191,36,0.08); border:1px solid rgba(251,191,36,0.2); border-radius:10px; padding:14px 18px; margin-bottom:12px;"><span style="color:#fbbf24 !important; font-weight:600;">⏳ {pending_count} pesanan menunggu konfirmasi supplier via email</span></div>', unsafe_allow_html=True)
        for o in pending:
            st.markdown(f"""
            <div class="order-card" style="border-left:3px solid #fbbf24;">
                <span style="color:#fbbf24 !important; font-weight:700;">#{o[0]}</span>
                <span style="color:#94a3b8 !important;"> · {o[1]} · {o[2]}g · {o[3]}</span>
                <span style="float:right; color:#475569 !important; font-size:11px;">{o[4]}</span>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.2); border-radius:10px; padding:14px 18px;">
            <span style="color:#10b981 !important; font-weight:600;">✓ Semua pesanan sudah dikonfirmasi</span>
        </div>""", unsafe_allow_html=True)

# ==================== TAB 4: ACTIVITY LOG ====================
with tab4:
    logs = get_activity_log(30)
    if not logs:
        st.markdown("""
        <div style="text-align:center; padding:60px 0;">
            <div style="font-size:48px; margin-bottom:12px;">📋</div>
            <p style="color:#475569 !important;">Belum ada aktivitas tercatat</p>
        </div>""", unsafe_allow_html=True)
    else:
        for log in logs:
            icons = {"system":"🤖","supplier":"📧","admin":"👤"}
            colors = {"CREATE_ORDER":"#f59e0b","CONFIRM_ORDER":"#22c55e","REJECT_ORDER":"#ef4444","RESTOCK":"#3b82f6"}
            ic = icons.get(log[4],"❓")
            ac = colors.get(log[1],"#64748b")
            st.markdown(f"""
            <div class="log-item" style="border-left-color:{ac};">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span>{ic}</span>
                        <span style="color:{ac} !important; font-weight:700; font-size:12px; letter-spacing:0.5px; margin:0 6px;">{log[1]}</span>
                        <span style="color:#cbd5e1 !important; font-size:13px;">{log[2]}</span>
                    </div>
                    <span style="color:#475569 !important; font-size:11px; white-space:nowrap;">{log[5]}</span>
                </div>
                <div style="margin-top:4px;"><span style="color:#475569 !important; font-size:11px;">{log[3]} · {log[4]}</span></div>
            </div>""", unsafe_allow_html=True)

# ==================== TAB 5: SIMULASI AGENT ====================
with tab5:
    # --- Session State ---
    if 'sim_running' not in st.session_state:
        st.session_state['sim_running'] = False
    if 'sim_logs' not in st.session_state:
        st.session_state['sim_logs'] = []
    if 'sim_step' not in st.session_state:
        st.session_state['sim_step'] = 0

    # --- Eksekusi step jika sedang berjalan (sebelum render agar data terbaru) ---
    if st.session_state['sim_running']:
        from main import run_simulation_step  # pyrefly: ignore
        from db import init_db  # pyrefly: ignore
        from fase_sim import init_fase  # pyrefly: ignore
        if st.session_state['sim_step'] == 0:
            init_db()
            init_fase()
            st.session_state['sim_logs'] = [
                "═" * 50,
                "🤖 Sistem Agentic AI TPS 3R Dimulai",
                "🌐 Confirm Server: http://localhost:5050",
                "═" * 50,
            ]
        step_logs = run_simulation_step()
        st.session_state['sim_step'] += 1
        st.session_state['sim_logs'].append(f"─── Siklus #{st.session_state['sim_step']} ───")
        st.session_state['sim_logs'].extend(step_logs)
        # Cap log agar tidak terlalu besar
        if len(st.session_state['sim_logs']) > 300:
            st.session_state['sim_logs'] = st.session_state['sim_logs'][-300:]

    # --- Header ---
    st.markdown("""
    <div style="margin-bottom:20px;">
        <h2 style="margin:0 0 6px; font-size:22px; color:#f1f5f9 !important; font-weight:800;"><span class="material-symbols-rounded" style="vertical-align:middle; font-size:26px; color:#818cf8;">smart_toy</span> Simulasi Agen AI</h2>
        <p style="margin:0; font-size:13px; color:#64748b !important;">
            Menjalankan siklus otomatis terus-menerus — sama seperti
            <code style="color:#a5b4fc; background:rgba(99,102,241,0.15); padding:2px 8px; border-radius:4px;">python main.py</code>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # --- Kontrol ---
    ctrl1, ctrl2, ctrl3, ctrl_status = st.columns([1, 1, 1, 2])
    with ctrl1:
        if st.button("Mulai Simulasi", use_container_width=True, disabled=st.session_state['sim_running']):
            st.session_state['sim_running'] = True
            st.rerun()
    with ctrl2:
        if st.button("Hentikan", use_container_width=True, disabled=not st.session_state['sim_running']):
            st.session_state['sim_running'] = False
            st.session_state['sim_logs'].append("Simulasi dihentikan oleh pengguna.")
            st.rerun()
    with ctrl3:
        if st.button("Reset Log", use_container_width=True):
            st.session_state['sim_logs'] = []
            st.session_state['sim_step'] = 0
            st.session_state['sim_running'] = False
            st.rerun()
    with ctrl_status:
        if st.session_state['sim_running']:
            st.markdown(f"""
            <div style="background:rgba(16,185,129,0.1); border:1px solid rgba(16,185,129,0.25); border-radius:10px; padding:10px 16px; display:flex; align-items:center; gap:10px;">
                <span style="color:#10b981 !important; font-size:18px; animation:pulse-dot 1.5s infinite;">●</span>
                <span style="color:#10b981 !important; font-weight:700;">RUNNING</span>
                <span style="color:#64748b !important; font-size:12px; margin-left:auto;">Siklus #{st.session_state['sim_step']}</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            _stxt = "SIAP" if st.session_state['sim_step'] == 0 else f"BERHENTI · Siklus #{st.session_state['sim_step']}"
            st.markdown(f"""
            <div style="background:rgba(100,116,139,0.08); border:1px solid rgba(100,116,139,0.2); border-radius:10px; padding:10px 16px; display:flex; align-items:center; gap:10px;">
                <span style="color:#64748b !important; font-size:18px;">●</span>
                <span style="color:#94a3b8 !important; font-weight:700;">{_stxt}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    # --- Terminal + Info Panel ---
    term_col, info_col = st.columns([3, 1])

    with term_col:
        # Build log HTML dengan warna berdasarkan jenis pesan
        _log_parts = []
        for _line in st.session_state.get('sim_logs', []):
            _esc = _line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if any(s in _line for s in ["══", "──"]):
                _log_parts.append(f'<div style="color:#6366f1 !important; padding:6px 0 2px; font-weight:700; opacity:0.8;">{_esc}</div>')
            elif "⚠️" in _line:
                _log_parts.append(f'<div style="color:#fbbf24 !important; padding:1px 0;"><span class="material-symbols-rounded" style="font-size:14px; vertical-align:middle;">warning</span> {_esc.replace("⚠️","").strip()}</div>')
            elif "✅" in _line:
                _log_parts.append(f'<div style="color:#22c55e !important; padding:1px 0;"><span class="material-symbols-rounded" style="font-size:14px; vertical-align:middle;">check_circle</span> {_esc.replace("✅","").strip()}</div>')
            elif "🧬" in _line:
                _log_parts.append(f'<div style="color:#a78bfa !important; padding:1px 0;"><span class="material-symbols-rounded" style="font-size:14px; vertical-align:middle;">science</span> {_esc.replace("🧬","").strip()}</div>')
            elif "📧" in _line:
                _log_parts.append(f'<div style="color:#60a5fa !important; padding:1px 0;"><span class="material-symbols-rounded" style="font-size:14px; vertical-align:middle;">mail</span> {_esc.replace("📧","").strip()}</div>')
            elif "⏳" in _line:
                _log_parts.append(f'<div style="color:#f59e0b !important; padding:1px 0;"><span class="material-symbols-rounded" style="font-size:14px; vertical-align:middle;">hourglass_empty</span> {_esc.replace("⏳","").strip()}</div>')
            elif "🔄" in _line:
                _log_parts.append(f'<div style="color:#22d3ee !important; padding:1px 0;"><span class="material-symbols-rounded" style="font-size:14px; vertical-align:middle;">sync</span> {_esc.replace("🔄","").strip()}</div>')
            elif "📦" in _line:
                _log_parts.append(f'<div style="color:#3b82f6 !important; padding:1px 0;"><span class="material-symbols-rounded" style="font-size:14px; vertical-align:middle;">inventory_2</span> {_esc.replace("📦","").strip()}</div>')
            elif any(s in _line for s in ["🛑", "❌", "⏹️"]):
                _log_parts.append(f'<div style="color:#ef4444 !important; padding:1px 0;"><span class="material-symbols-rounded" style="font-size:14px; vertical-align:middle;">cancel</span> {_esc.replace("🛑","").replace("❌","").replace("⏹️","").strip()}</div>')
            elif "🤖" in _line:
                _log_parts.append(f'<div style="color:#818cf8 !important; padding:1px 0; font-weight:600;"><span class="material-symbols-rounded" style="font-size:14px; vertical-align:middle;">smart_toy</span> {_esc.replace("🤖","").strip()}</div>')
            elif "🌐" in _line:
                _log_parts.append(f'<div style="color:#6366f1 !important; padding:1px 0;"><span class="material-symbols-rounded" style="font-size:14px; vertical-align:middle;">public</span> {_esc.replace("🌐","").strip()}</div>')
            else:
                _log_parts.append(f'<div style="color:#94a3b8 !important; padding:1px 0;">{_esc}</div>')

        _log_html = "".join(_log_parts) if _log_parts else '<div style="color:#475569 !important; text-align:center; padding:60px 0; font-size:14px;">Klik <b style="color:#a5b4fc !important;">Mulai Simulasi</b> untuk memulai</div>'

        st.markdown(f"""
<div style="background:rgba(6,9,24,0.95); border:1px solid rgba(99,102,241,0.15); border-radius:14px; overflow:hidden;">
    <div style="background:rgba(15,23,42,0.9); padding:10px 20px; border-bottom:1px solid rgba(99,102,241,0.1); display:flex; align-items:center; gap:8px;">
        <span style="width:10px; height:10px; border-radius:50%; background:#ef4444; display:inline-block;"></span>
        <span style="width:10px; height:10px; border-radius:50%; background:#fbbf24; display:inline-block;"></span>
        <span style="width:10px; height:10px; border-radius:50%; background:#22c55e; display:inline-block;"></span>
        <span style="color:#64748b !important; font-size:12px; margin-left:8px; font-family:'JetBrains Mono',monospace;">Terminal — python main.py</span>
    </div>
    <div style="padding:16px 20px; font-family:'JetBrains Mono','Fira Code','Cascadia Code','Courier New',monospace; max-height:500px; overflow-y:auto; font-size:12.5px; line-height:1.7;">
        {_log_html}
    </div>
</div>
""", unsafe_allow_html=True)


    with info_col:
        from db import get_stock as _sim_get_stock, get_fase as _sim_get_fase  # pyrefly: ignore
        _cs, _ct, _cu = _sim_get_stock("starter_maggot")
        _cf = _sim_get_fase()
        _fn = _cf['nama'] if _cf else "N/A"
        _fp = _cf['progress'] if _cf else 0
        _stock_color = '#ef4444' if _cs <= _ct else '#22c55e'

        st.markdown(f"""
<div style="background:rgba(15,23,42,0.8); border:1px solid rgba(99,102,241,0.15); border-radius:14px; padding:20px;">
<div style="font-size:11px; color:#64748b !important; text-transform:uppercase; letter-spacing:1px; margin-bottom:16px; font-weight:600;">Status Real-time</div>
<div style="margin-bottom:16px;">
<div style="font-size:11px; color:#64748b !important; margin-bottom:4px;"><span class="material-symbols-rounded" style="font-size:12px; vertical-align:middle; color:#818cf8;">update</span> Siklus ke-</div>
<div style="font-size:28px; font-weight:800; color:#818cf8 !important;">{st.session_state['sim_step']}</div>
</div>
<div style="height:1px; background:rgba(99,102,241,0.1); margin:12px 0;"></div>
<div style="margin-bottom:16px;">
<div style="font-size:11px; color:#64748b !important; margin-bottom:4px;"><span class="material-symbols-rounded" style="font-size:12px; vertical-align:middle; color:#3b82f6;">inventory_2</span> Stok Pakan</div>
<div style="font-size:20px; font-weight:700; color:{_stock_color} !important;">{_cs:.0f} <span style="font-size:12px; color:#64748b !important;">{_cu}</span></div>
<div style="font-size:10px; color:#475569 !important;">Threshold: {_ct:.0f}</div>
</div>
<div style="height:1px; background:rgba(99,102,241,0.1); margin:12px 0;"></div>
<div style="margin-bottom:16px;">
<div style="font-size:11px; color:#64748b !important; margin-bottom:4px;"><span class="material-symbols-rounded" style="font-size:12px; vertical-align:middle; color:#a78bfa;">science</span> Fase Aktif</div>
<div style="font-size:16px; font-weight:700; color:#a78bfa !important;">{str(_fn).replace('_',' ').title()}</div>
<div style="margin-top:6px; background:rgba(30,41,59,0.8); border-radius:6px; overflow:hidden; height:6px;">
<div style="width:{_fp:.0f}%; height:100%; background:linear-gradient(90deg,#818cf8,#6366f1); border-radius:6px;"></div>
</div>
<div style="font-size:10px; color:#475569 !important; margin-top:4px;">{_fp:.1f}%</div>
</div>
<div style="height:1px; background:rgba(99,102,241,0.1); margin:12px 0;"></div>
<div>
<div style="font-size:11px; color:#64748b !important; margin-bottom:4px;"><span class="material-symbols-rounded" style="font-size:12px; vertical-align:middle; color:#94a3b8;">list_alt</span> Total Log</div>
<div style="font-size:14px; font-weight:600; color:#94a3b8 !important;">{len(st.session_state.get('sim_logs', []))} <span style="font-size:11px;">baris</span></div>
</div>
</div>
""", unsafe_allow_html=True)

    # --- Auto-rerun saat simulasi berjalan ---
    if st.session_state['sim_running']:
        import time
        time.sleep(3)
        st.rerun()

# ---- Footer ----
st.markdown("""
<div style="text-align:center; margin-top:32px; padding-top:16px; border-top:1px solid rgba(51,65,85,0.3);">
    <p style="color:#334155 !important; font-size:11px; letter-spacing:1px;">TPS 3R SMART OPERATIONS · AGENTIC AI SYSTEM</p>
</div>
""", unsafe_allow_html=True)

conn.close()