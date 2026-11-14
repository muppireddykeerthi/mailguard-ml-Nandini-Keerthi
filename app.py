"""MailGuard ML - Streamlit entry point.

Run locally:
    streamlit run app.py
"""

from __future__ import annotations

import base64
import pathlib
import random

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="MailGuard ML",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.app_resources import get_model_bundle, get_service  # noqa: E402


def html(markup: str) -> None:
    """Render HTML safely.

    Streamlit's markdown parser turns any line indented by 4+ spaces into a
    code block, which is what made raw <div> tags show up on the page.
    Stripping every line's indentation and joining them avoids that.
    """
    flat = "".join(line.strip() for line in markup.splitlines())
    st.markdown(flat, unsafe_allow_html=True)


# ============================================================
# ANIMATED SPAM / NOT-SPAM VERDICT
# ============================================================

_CSS = """
<style>
@property --num { syntax: '<integer>'; initial-value: 0; inherits: false; }

@keyframes vdPop     { 0% {opacity:0; transform:scale(.85) translateY(20px);} 70% {transform:scale(1.03);} 100% {opacity:1; transform:scale(1) translateY(0);} }
@keyframes vdShake   { 0%,100% {transform:translateX(0);} 15% {transform:translateX(-12px);} 30% {transform:translateX(10px);} 45% {transform:translateX(-8px);} 60% {transform:translateX(6px);} 75% {transform:translateX(-3px);} }
@keyframes vdBorderRed { 0%,100% {box-shadow:0 0 0 0 rgba(239,68,68,.55), 0 14px 34px rgba(239,68,68,.25);} 50% {box-shadow:0 0 0 12px rgba(239,68,68,0), 0 14px 34px rgba(239,68,68,.45);} }
@keyframes vdBorderGreen { 0%,100% {box-shadow:0 0 0 0 rgba(34,197,94,.5), 0 14px 34px rgba(34,197,94,.22);} 50% {box-shadow:0 0 0 12px rgba(34,197,94,0), 0 14px 34px rgba(34,197,94,.4);} }
@keyframes vdWarn    { 0%,100% {transform:scale(1) rotate(0);} 25% {transform:scale(1.18) rotate(-8deg);} 75% {transform:scale(1.18) rotate(8deg);} }
@keyframes vdRipple  { 0% {transform:scale(.6); opacity:.7;} 100% {transform:scale(2.2); opacity:0;} }
@keyframes vdDrawCircle { to {stroke-dashoffset:0;} }
@keyframes vdDrawCheck  { to {stroke-dashoffset:0;} }
@keyframes vdBounce  { 0% {transform:scale(.3);} 60% {transform:scale(1.15);} 100% {transform:scale(1);} }
@keyframes vdFill    { from {width:0;} to {width:var(--w);} }
@keyframes vdCount   { from {--num:0;} to {--num:var(--target);} }
@keyframes vdConfetti{ 0% {transform:translateY(-20px) rotate(0); opacity:1;} 100% {transform:translateY(260px) rotate(540deg); opacity:0;} }
@keyframes vdFlash   { 0%,100% {opacity:1;} 50% {opacity:.55;} }
@keyframes vdSlideUp { from {opacity:0; transform:translateY(14px);} to {opacity:1; transform:translateY(0);} }

.vd-card { position:relative; overflow:hidden; border-radius:22px; padding:28px 30px; margin:14px 0 8px 0; display:flex; align-items:center; gap:26px; color:#fff; }
.vd-spam { background:linear-gradient(135deg,#7f1d1d,#dc2626 60%,#ef4444); animation:vdPop .6s ease both, vdShake .7s .55s ease both, vdBorderRed 1.8s 1.2s infinite; }
.vd-ham  { background:linear-gradient(135deg,#064e3b,#059669 60%,#22c55e); animation:vdPop .6s ease both, vdBorderGreen 2.2s 1s infinite; }

.vd-icon { position:relative; width:92px; height:92px; flex:0 0 92px; display:flex; align-items:center; justify-content:center; }
.vd-icon .ring { position:absolute; inset:0; border-radius:50%; border:3px solid rgba(255,255,255,.7); animation:vdRipple 1.8s ease-out infinite; }
.vd-icon .ring.r2 { animation-delay:.6s; }
.vd-icon .ring.r3 { animation-delay:1.2s; }
.vd-warn { font-size:58px; animation:vdWarn 1.1s ease-in-out infinite; position:relative; }
.vd-check { position:relative; width:84px; height:84px; animation:vdBounce .7s .5s ease both; }
.vd-check circle { stroke:#fff; stroke-width:4; fill:rgba(255,255,255,.15); stroke-dasharray:252; stroke-dashoffset:252; animation:vdDrawCircle .7s .2s ease forwards; }
.vd-check path   { stroke:#fff; stroke-width:6; fill:none; stroke-linecap:round; stroke-linejoin:round; stroke-dasharray:60; stroke-dashoffset:60; animation:vdDrawCheck .5s .8s ease forwards; }

.vd-body { flex:1; min-width:0; }
.vd-label { font-size:13px; font-weight:700; letter-spacing:1.6px; text-transform:uppercase; opacity:.85; animation:vdSlideUp .5s .3s ease both; }
.vd-title { font-size:38px; font-weight:800; letter-spacing:-.6px; line-height:1.1; margin:4px 0 6px 0; animation:vdSlideUp .5s .4s ease both; }
.vd-spam .vd-title { animation:vdSlideUp .5s .4s ease both, vdFlash 1.4s 1.2s infinite; }
.vd-sub { font-size:15px; opacity:.92; animation:vdSlideUp .5s .5s ease both; }

.vd-pct { font-size:46px; font-weight:800; line-height:1; text-align:right; animation:vdCount 1.4s .4s ease-out both; counter-reset:n var(--num); }
.vd-pct::after { content:counter(n) "%"; }
.vd-pct-label { font-size:12px; opacity:.85; text-align:right; margin-top:4px; letter-spacing:.8px; text-transform:uppercase; }

.vd-barwrap { margin:10px 0 18px 0; animation:vdSlideUp .5s .6s ease both; }
.vd-bartrack { height:14px; border-radius:999px; background:#e2e8f0; overflow:hidden; }
.vd-barfill { height:100%; width:0; border-radius:999px; animation:vdFill 1.4s .6s cubic-bezier(.2,.8,.2,1) forwards; }
.vd-barfill.spam { background:linear-gradient(90deg,#f97316,#ef4444); }
.vd-barfill.ham  { background:linear-gradient(90deg,#22c55e,#10b981); }
.vd-barmeta { display:flex; justify-content:space-between; font-size:12px; color:#64748b; margin-top:6px; }

.vd-cf { position:absolute; top:0; width:9px; height:16px; border-radius:2px; opacity:0; animation:vdConfetti 2.8s ease-in forwards; pointer-events:none; }
.vd-sp { position:absolute; top:-10px; font-size:20px; opacity:0; animation:vdConfetti 3s ease-in forwards; pointer-events:none; }

@media (max-width: 700px) { .vd-card { flex-direction:column; text-align:center; } .vd-pct, .vd-pct-label { text-align:center; } }
@media (prefers-reduced-motion: reduce) { .vd-card *, .vd-card, .vd-barfill { animation:none !important; } .vd-barfill { width:var(--w); } .vd-check circle, .vd-check path { stroke-dashoffset:0; } }
</style>
"""


def render_verdict(is_spam: bool, probability: float, threshold: float | None = None) -> None:
    """Show an animated verdict card + probability bar."""
    prob = max(0.0, min(1.0, float(probability)))
    pct = round(prob * 100)

    html(_CSS)

    rnd = random.Random(42)

    if is_spam:
        # falling warning symbols
        pieces = "".join(
            f'<span class="vd-sp" style="left:{rnd.randint(2, 96)}%;animation-delay:{rnd.random() * 1.6:.2f}s">'
            f'{rnd.choice(["⚠️", "🚫", "✖️"])}</span>'
            for _ in range(10)
        )
        icon = (
            '<div class="vd-icon"><span class="ring"></span><span class="ring r2"></span>'
            '<span class="ring r3"></span><span class="vd-warn">🚨</span></div>'
        )
        card_cls, label, title = "vd-spam", "Threat detected", "Spam Detected"
        sub = "This email looks suspicious. Avoid clicking links or opening attachments."
        bar_cls = "spam"
    else:
        colors = ["#bbf7d0", "#fde68a", "#bfdbfe", "#fbcfe8", "#ffffff", "#a7f3d0"]
        pieces = "".join(
            f'<i class="vd-cf" style="left:{rnd.randint(2, 98)}%;background:{rnd.choice(colors)};'
            f'animation-delay:{rnd.random() * 1.4:.2f}s"></i>'
            for _ in range(36)
        )
        icon = (
            '<div class="vd-icon"><span class="ring"></span><span class="ring r2"></span>'
            '<svg class="vd-check" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40"/>'
            '<path d="M30 52 L45 67 L72 36"/></svg></div>'
        )
        card_cls, label, title = "vd-ham", "All clear", "Not Spam"
        sub = "This email looks legitimate and safe."
        bar_cls = "ham"

    html(
        f"""
        <div class="vd-card {card_cls}">
            {pieces}
            {icon}
            <div class="vd-body">
                <div class="vd-label">{label}</div>
                <div class="vd-title">{title}</div>
                <div class="vd-sub">{sub}</div>
            </div>
            <div>
                <div class="vd-pct" style="--target:{pct}"></div>
                <div class="vd-pct-label">Spam probability</div>
            </div>
        </div>
        """
    )

    thr_text = f"Threshold {threshold:.2f}" if threshold is not None else "&nbsp;"
    html(
        f"""
        <div class="vd-barwrap">
            <div class="vd-bartrack"><div class="vd-barfill {bar_cls}" style="--w:{pct}%"></div></div>
            <div class="vd-barmeta"><span>0% · Safe</span><span>{thr_text}</span><span>Spam · 100%</span></div>
        </div>
        """
    )

    # Extra Streamlit-native effects
    if is_spam:
        st.toast("Spam detected!", icon="🚨")
    else:
        st.balloons()


# Make the function reachable from views/analyzer.py without importing app.py:
#     st.session_state["render_verdict"](is_spam=..., probability=..., threshold=...)
st.session_state["render_verdict"] = render_verdict


# ============================================================
# THEME / CSS
# ============================================================

html(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@600;700&family=Inter:wght@400;500;600;700;800&display=swap');

    :root {
        --navy-900: #0b1220;
        --navy-800: #111c33;
        --blue-700: #1d4ed8;
        --blue-500: #3b82f6;
        --blue-100: #dbeafe;
        --slate-900: #0f172a;
        --slate-600: #475569;
        --slate-500: #64748b;
        --slate-200: #e2e8f0;
        --bg: #f5f7fb;
    }

    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* ---------- App background ---------- */
    .stApp {
        background: var(--bg);
    }

    /* Transparent top bar (removes the white strip) */
    header[data-testid="stHeader"] {
        background: transparent;
    }

    .block-container {
        padding: 1.5rem 2.5rem 3rem 2.5rem;
        max-width: 1400px;
    }

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0b1220 0%, #0f1f4d 60%, #1e3a8a 100%);
        border-right: 1px solid rgba(255,255,255,0.06);
    }
    section[data-testid="stSidebar"] * {
        color: #e8eefc;
    }
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.15);
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
        border-radius: 10px;
        padding: 6px 10px;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
        background: rgba(255,255,255,0.10);
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-current="page"] {
        background: rgba(59,130,246,0.35);
        font-weight: 600;
    }

    /* ---------- Sidebar brand ---------- */
    .brand {
        text-align: center;
        padding: 6px 0 14px 0;
    }
    .brand-logo {
        width: 64px;
        height: 64px;
        margin: 0 auto 10px auto;
        border-radius: 18px;
        background: linear-gradient(135deg, #3b82f6, #1d4ed8);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 32px;
        box-shadow: 0 8px 20px rgba(59,130,246,0.45);
    }
    .brand-name {
        font-size: 22px;
        font-weight: 800;
        letter-spacing: -0.3px;
        color: #ffffff;
    }
    .brand-tag {
        font-size: 12px;
        color: #93c5fd !important;
        margin-top: 2px;
    }

    /* ---------- Sidebar cards ---------- */
    .side-card {
        background: rgba(255,255,255,0.07);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 14px;
        padding: 14px 16px;
        margin-top: 12px;
    }
    .side-card-title {
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        color: #93c5fd !important;
        margin-bottom: 8px;
    }
    .side-row {
        font-size: 14px;
        padding: 3px 0;
        color: #ffffff;
    }
    .dot {
        display: inline-block;
        width: 9px;
        height: 9px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .dot-green { background: #22c55e; box-shadow: 0 0 8px #22c55e; }
    .dot-red   { background: #ef4444; box-shadow: 0 0 8px #ef4444; }

    .avatar {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background: linear-gradient(135deg, #60a5fa, #2563eb);
        font-size: 12px;
        font-weight: 700;
        margin-right: 10px;
        color: white;
    }

    /* ---------- Hero ---------- */
    .hero {
        position: relative;
        overflow: hidden;
        background: linear-gradient(120deg, #0b1220 0%, #1e3a8a 55%, #2563eb 100%);
        padding: 26px 32px;
        border-radius: 20px;
        margin-bottom: 22px;
        box-shadow: 0 14px 34px rgba(30,58,138,0.25);
    }
    .hero::after {
        content: "";
        position: absolute;
        right: -60px;
        top: -60px;
        width: 240px;
        height: 240px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(255,255,255,0.18), transparent 70%);
    }
    .hero-title {
        color: #ffffff;
        font-size: 32px;
        font-weight: 800;
        letter-spacing: -0.6px;
        line-height: 1.15;
    }
    .hero-subtitle {
        color: #cfe0ff;
        font-size: 15px;
        margin-top: 6px;
    }
    .chips {
        margin-top: 16px;
    }
    .chip {
        display: inline-block;
        background: rgba(255,255,255,0.14);
        border: 1px solid rgba(255,255,255,0.22);
        color: #ffffff;
        font-size: 12.5px;
        font-weight: 600;
        padding: 5px 12px;
        border-radius: 999px;
        margin-right: 8px;
        margin-bottom: 4px;
    }
    .hero-credit {
        color: #bcd2ff;
        font-size: 13px;
        margin-top: 14px;
    }

    /* ---------- Main content polish ---------- */
    h1, h2, h3 {
        color: var(--slate-900);
        letter-spacing: -0.3px;
    }

    .stButton > button,
    .stDownloadButton > button {
        border-radius: 10px;
        font-weight: 600;
        padding: 0.5rem 1.2rem;
        transition: all 0.15s ease;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        border: none;
        color: #ffffff;
        box-shadow: 0 6px 16px rgba(37,99,235,0.35);
    }
    .stButton > button:hover {
        transform: translateY(-1px);
    }

    .stTextArea textarea, .stTextInput input {
        border-radius: 12px;
        border: 1px solid var(--slate-200);
        background: #ffffff;
    }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid var(--slate-200);
        border-radius: 14px;
        padding: 14px 16px;
        box-shadow: 0 3px 12px rgba(15,23,42,0.05);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 8px 14px;
        font-weight: 600;
    }

    div[data-testid="stExpander"] {
        background: #ffffff;
        border: 1px solid var(--slate-200);
        border-radius: 12px;
    }

    /* ---------- Footer ---------- */
    .footer {
        text-align: center;
        color: var(--slate-500);
        font-size: 13px;
        margin-top: 40px;
        padding: 18px 0 4px 0;
        border-top: 1px solid var(--slate-200);
    }

    /* ============================================================
       ANIMATIONS
       ============================================================ */

    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(22px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to   { opacity: 1; }
    }
    @keyframes slideInLeft {
        from { opacity: 0; transform: translateX(-24px); }
        to   { opacity: 1; transform: translateX(0); }
    }
    @keyframes popIn {
        0%   { opacity: 0; transform: scale(0.8); }
        70%  { transform: scale(1.06); }
        100% { opacity: 1; transform: scale(1); }
    }
    @keyframes gradientShift {
        0%   { background-position: 0% 50%; }
        50%  { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    @keyframes floatY {
        0%, 100% { transform: translateY(0); }
        50%      { transform: translateY(-8px); }
    }
    @keyframes orbDrift {
        0%, 100% { transform: translate(0, 0) scale(1); }
        50%      { transform: translate(-30px, 20px) scale(1.15); }
    }
    @keyframes pulseGreen {
        0%   { box-shadow: 0 0 0 0 rgba(34,197,94,0.7); }
        70%  { box-shadow: 0 0 0 10px rgba(34,197,94,0); }
        100% { box-shadow: 0 0 0 0 rgba(34,197,94,0); }
    }
    @keyframes pulseRed {
        0%   { box-shadow: 0 0 0 0 rgba(239,68,68,0.7); }
        70%  { box-shadow: 0 0 0 10px rgba(239,68,68,0); }
        100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); }
    }
    @keyframes glowPulse {
        0%, 100% { box-shadow: 0 8px 20px rgba(59,130,246,0.45); }
        50%      { box-shadow: 0 8px 34px rgba(96,165,250,0.85); }
    }
    @keyframes shimmer {
        0%   { background-position: -200% center; }
        100% { background-position: 200% center; }
    }
    @keyframes sheen {
        0%   { transform: translateX(-120%) skewX(-20deg); }
        60%, 100% { transform: translateX(260%) skewX(-20deg); }
    }

    /* ---------- Page load ---------- */
    .block-container {
        animation: fadeIn 0.6s ease both;
    }

    /* ---------- Hero ---------- */
    .hero {
        background-size: 300% 300%;
        animation: fadeUp 0.7s ease both, gradientShift 12s ease infinite;
    }
    .hero-title {
        background: linear-gradient(90deg, #ffffff 0%, #93c5fd 25%, #ffffff 50%, #93c5fd 75%, #ffffff 100%);
        background-size: 200% auto;
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: shimmer 6s linear infinite;
    }
    .hero-title-row {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .hero-emoji {
        font-size: 34px;
        display: inline-block;
        animation: floatY 3s ease-in-out infinite;
    }
    .hero-title { display: inline-block; }
    .hero-subtitle { animation: fadeUp 0.8s 0.15s ease both; }
    .hero-credit   { animation: fadeUp 0.8s 0.55s ease both; }

    .chip {
        animation: popIn 0.6s ease both;
        transition: transform 0.2s ease, background 0.2s ease;
        cursor: default;
    }
    .chip:nth-child(1) { animation-delay: 0.30s; }
    .chip:nth-child(2) { animation-delay: 0.42s; }
    .chip:nth-child(3) { animation-delay: 0.54s; }
    .chip:hover {
        transform: translateY(-3px) scale(1.05);
        background: rgba(255,255,255,0.28);
    }

    /* Floating glow orbs inside hero */
    .orb {
        position: absolute;
        border-radius: 50%;
        pointer-events: none;
        filter: blur(2px);
        animation: orbDrift 9s ease-in-out infinite;
    }
    .orb1 {
        width: 140px; height: 140px;
        right: 12%; bottom: -50px;
        background: radial-gradient(circle, rgba(147,197,253,0.40), transparent 70%);
    }
    .orb2 {
        width: 90px; height: 90px;
        right: 32%; top: -30px;
        background: radial-gradient(circle, rgba(255,255,255,0.25), transparent 70%);
        animation-duration: 12s;
        animation-delay: -4s;
    }

    /* Light sheen sweeping across the hero */
    .hero::before {
        content: "";
        position: absolute;
        top: 0; left: 0;
        width: 35%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.14), transparent);
        animation: sheen 7s ease-in-out infinite;
        pointer-events: none;
    }

    /* ---------- Sidebar ---------- */
    .brand-logo {
        animation: floatY 3.5s ease-in-out infinite, glowPulse 3.5s ease-in-out infinite;
    }
    .brand-name { animation: fadeUp 0.7s 0.1s ease both; }
    .brand-tag  { animation: fadeUp 0.7s 0.2s ease both; }

    .side-card {
        animation: slideInLeft 0.6s ease both;
        transition: transform 0.25s ease, background 0.25s ease, border-color 0.25s ease;
    }
    .side-card:nth-of-type(1) { animation-delay: 0.20s; }
    .side-card:nth-of-type(2) { animation-delay: 0.35s; }
    .side-card:hover {
        transform: translateX(4px);
        background: rgba(255,255,255,0.12);
        border-color: rgba(147,197,253,0.5);
    }

    .dot-green { animation: pulseGreen 1.8s infinite; }
    .dot-red   { animation: pulseRed 1.8s infinite; }

    .avatar { transition: transform 0.25s ease; }
    .side-row:hover .avatar { transform: scale(1.18) rotate(-8deg); }

    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a {
        transition: background 0.2s ease, transform 0.2s ease;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a:hover {
        transform: translateX(5px);
    }

    /* ---------- Main content ---------- */
    div[data-testid="stMetric"] {
        animation: fadeUp 0.6s ease both;
        transition: transform 0.25s ease, box-shadow 0.25s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 14px 28px rgba(37,99,235,0.18);
    }

    div[data-testid="stExpander"] {
        transition: box-shadow 0.25s ease, transform 0.25s ease;
    }
    div[data-testid="stExpander"]:hover {
        box-shadow: 0 8px 20px rgba(15,23,42,0.08);
        transform: translateY(-2px);
    }

    .stTextArea textarea, .stTextInput input {
        transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 4px rgba(59,130,246,0.18);
    }

    .stButton > button, .stDownloadButton > button {
        position: relative;
        overflow: hidden;
    }
    .stButton > button:hover {
        box-shadow: 0 10px 22px rgba(37,99,235,0.35);
    }
    .stButton > button:active {
        transform: scale(0.97);
    }
    .stButton > button[kind="primary"]::after {
        content: "";
        position: absolute;
        top: 0; left: 0;
        width: 40%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.35), transparent);
        animation: sheen 3.5s ease-in-out infinite;
    }

    .stTabs [data-baseweb="tab"] {
        transition: background 0.2s ease, color 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(59,130,246,0.10);
    }

    div[data-testid="stAlert"],
    div[data-testid="stDataFrame"],
    div[data-testid="stPlotlyChart"],
    div[data-testid="stImage"] {
        animation: fadeUp 0.6s ease both;
    }

    .footer { animation: fadeIn 1.2s 0.5s ease both; }

    /* ---------- Respect users who prefer reduced motion ---------- */
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation: none !important;
            transition: none !important;
        }
    }

    /* ---------- Auto spam / not-spam effects on st.error / st.success alerts ---------- */
    @keyframes mgShake { 0%,100%{transform:translateX(0);} 15%{transform:translateX(-12px);} 30%{transform:translateX(10px);} 45%{transform:translateX(-8px);} 60%{transform:translateX(6px);} 75%{transform:translateX(-3px);} }
    @keyframes mgPopIn { 0%{opacity:0;transform:scale(.9);} 70%{transform:scale(1.03);} 100%{opacity:1;transform:scale(1);} }
    @keyframes mgPulseRed { 0%,100%{box-shadow:0 0 0 0 rgba(239,68,68,.55);} 50%{box-shadow:0 0 0 12px rgba(239,68,68,0);} }
    @keyframes mgPulseGreen { 0%,100%{box-shadow:0 0 0 0 rgba(34,197,94,.5);} 50%{box-shadow:0 0 0 12px rgba(34,197,94,0);} }
    @keyframes mgConfetti { 0%{transform:translateY(-10px) rotate(0);opacity:1;} 100%{transform:translateY(220px) rotate(540deg);opacity:0;} }
    div[data-testid="stAlert"].mg-spam { animation: mgShake .7s ease both, mgPulseRed 1.8s .8s infinite; border: 2px solid #ef4444; border-radius: 14px; position: relative; }
    div[data-testid="stAlert"].mg-ham  { animation: mgPopIn .6s ease both, mgPulseGreen 2.2s .8s infinite; border: 2px solid #22c55e; border-radius: 14px; position: relative; }
    .mg-cf { position:absolute; top:0; width:8px; height:14px; border-radius:2px; pointer-events:none; animation: mgConfetti 2.6s ease-in forwards; z-index:5; }
    @media (prefers-reduced-motion: reduce) { div[data-testid="stAlert"].mg-spam, div[data-testid="stAlert"].mg-ham, .mg-cf { animation:none !important; } }

    /* ============================================================
       LIVE SCANNER SLIDESHOW (sidebar)
       ============================================================ */
    @keyframes mgCycle { 0% {opacity:0; transform:translateX(26px);} 4% {opacity:1; transform:translateX(0);} 30% {opacity:1; transform:translateX(0);} 34% {opacity:0; transform:translateX(-26px);} 100% {opacity:0;} }
    @keyframes mgScenePop { 0% {opacity:0; transform:scale(.8);} 70% {transform:scale(1.05);} 100% {opacity:1; transform:scale(1);} }
    @keyframes mgFloat { 0%,100% {transform:translateY(0);} 50% {transform:translateY(-5px);} }
    @keyframes mgLaser { from {transform:translateY(0);} to {transform:translateY(74px);} }
    @keyframes mgSpin { to {transform:rotate(360deg);} }
    @keyframes mgBeat { 0%,100% {transform:scale(1);} 50% {transform:scale(1.05);} }
    @keyframes mgTick { 0% {stroke-dashoffset:70;} 40%,80% {stroke-dashoffset:0;} 100% {stroke-dashoffset:70;} }
    @keyframes mgTickOnce { from {stroke-dashoffset:40;} to {stroke-dashoffset:0;} }
    @keyframes mgBob { 0%,100% {transform:translateY(0);} 50% {transform:translateY(-7px);} }
    @keyframes mgDot { 0%,100% {transform:translateY(0); opacity:.4;} 50% {transform:translateY(-6px); opacity:1;} }
    @keyframes mgShakeS { 0%,45%,100% {transform:translateX(0);} 5% {transform:translateX(-7px);} 12% {transform:translateX(6px);} 19% {transform:translateX(-5px);} 26% {transform:translateX(4px);} 33% {transform:translateX(-2px);} }
    @keyframes mgWarn { 0%,100% {transform:scale(1);} 50% {transform:scale(1.14);} }
    @keyframes mgWave { 0% {transform:scale(.6); opacity:.9;} 100% {transform:scale(2.1); opacity:0;} }
    @keyframes mgBug { 0%,100% {transform:translateY(0) rotate(-8deg);} 50% {transform:translateY(-10px) rotate(8deg);} }
    @keyframes mgStamp { 0% {opacity:0; transform:rotate(-12deg) scale(2.6);} 60% {opacity:1; transform:rotate(-12deg) scale(.9);} 100% {opacity:1; transform:rotate(-12deg) scale(1);} }
    @keyframes mgBounce { 0% {transform:scale(0);} 60% {transform:scale(1.18);} 100% {transform:scale(1);} }
    @keyframes mgTwinkle { 0%,100% {transform:scale(.3); opacity:.2;} 50% {transform:scale(1.2); opacity:1;} }

    .mg-stage { position:relative; height:150px; border-radius:14px; overflow:hidden; background:radial-gradient(circle at 50% 40%, rgba(96,165,250,.28), rgba(8,15,35,.55)); border:1px solid rgba(255,255,255,.14); }
    .mg-stage::before, .mg-stage::after { content:''; position:absolute; inset:0; opacity:0; transition:opacity .5s ease; pointer-events:none; }
    .mg-stage::before { background:radial-gradient(circle at 50% 45%, rgba(239,68,68,.6), rgba(60,10,10,.55) 80%); }
    .mg-stage::after  { background:radial-gradient(circle at 50% 45%, rgba(34,197,94,.55), rgba(5,40,25,.55) 80%); }
    .mg-stage[data-scene='spam']::before { opacity:1; }
    .mg-stage[data-scene='ham']::after   { opacity:1; }

    .mg-sl { position:absolute; inset:0; opacity:0; z-index:1; pointer-events:none; }
    .mg-sl svg { width:100%; height:100%; display:block; }
    .mg-stage[data-scene='idle'] .sl-i1 { animation:mgCycle 12s infinite both; }
    .mg-stage[data-scene='idle'] .sl-i2 { animation:mgCycle 12s 4s infinite both; }
    .mg-stage[data-scene='idle'] .sl-i3 { animation:mgCycle 12s 8s infinite both; }
    .mg-stage[data-scene='scan'] .sl-scan { opacity:1; animation:mgScenePop .4s ease both; }
    .mg-stage[data-scene='spam'] .sl-spam { opacity:1; animation:mgScenePop .5s ease both; }
    .mg-stage[data-scene='ham']  .sl-ham  { opacity:1; animation:mgScenePop .5s ease both; }

    .mg-cap { text-align:center; font-size:13px; font-weight:700; letter-spacing:.5px; margin-top:10px; transition:color .3s ease; }
    .mg-cap[data-scene='scan'] { color:#bae6fd; }
    .mg-cap[data-scene='spam'] { color:#fecaca; }
    .mg-cap[data-scene='ham']  { color:#bbf7d0; }

    .g-float { animation:mgFloat 3s ease-in-out infinite; }
    .g-laser { animation:mgLaser 1.8s ease-in-out infinite alternate; }
    .g-ring  { transform-origin:120px 78px; animation:mgSpin 10s linear infinite; }
    .g-shield{ transform-origin:120px 78px; animation:mgBeat 2.4s ease-in-out infinite; }
    .g-tick  { stroke-dasharray:70; stroke-dashoffset:70; animation:mgTick 3s ease-in-out infinite; }
    .g-bob   { animation:mgBob 2.6s ease-in-out infinite; }
    .g-bob.b2{ animation-delay:-.9s; }
    .g-bob.b3{ animation-delay:-1.7s; }
    .g-orbit { transform-origin:120px 88px; animation:mgSpin 2s linear infinite; }
    .g-dot   { animation:mgDot 1s ease-in-out infinite; }
    .g-dot.d2{ animation-delay:.2s; }
    .g-dot.d3{ animation-delay:.4s; }
    .g-shake { transform-origin:120px 88px; animation:mgShakeS 1.8s ease-in-out infinite; }
    .g-warn  { transform-origin:120px 90px; animation:mgWarn 1s ease-in-out infinite; }
    .g-wave  { transform-box:fill-box; transform-origin:center; animation:mgWave 1.8s ease-out infinite; }
    .g-wave.w2 { animation-delay:.9s; }
    .g-bug   { animation:mgBug 2.2s ease-in-out infinite; }
    .g-bug.a2{ animation-delay:-.7s; }
    .g-bug.a3{ animation-delay:-1.4s; }
    .g-stamp { transform-box:fill-box; transform-origin:center; animation:mgStamp .6s .3s ease both; }
    .g-okc   { transform-box:fill-box; transform-origin:center; animation:mgBounce .7s .1s ease both; }
    .g-oktick{ stroke-dasharray:40; stroke-dashoffset:40; animation:mgTickOnce .5s .6s ease forwards; }
    .g-star  { transform-box:fill-box; transform-origin:center; animation:mgTwinkle 1.6s ease-in-out infinite; }
    .g-star.s2{ animation-delay:.4s; }
    .g-star.s3{ animation-delay:.8s; }
    .g-star.s4{ animation-delay:1.2s; }

    @media (prefers-reduced-motion: reduce) {
        .mg-stage[data-scene='idle'] .sl-i1 { opacity:1 !important; }
        .g-tick, .g-oktick { stroke-dashoffset:0 !important; }
    }

    /* ============================================================
       WELCOME PAGE
       ============================================================ */
    @keyframes wlUp { from {opacity:0; transform:translateY(26px);} to {opacity:1; transform:translateY(0);} }
    @keyframes wlWave { 0%,60%,100% {transform:rotate(0);} 10%,30% {transform:rotate(16deg);} 20%,40% {transform:rotate(-10deg);} 50% {transform:rotate(10deg);} }
    @keyframes wlPulse { 0% {transform:scale(.7); opacity:.7;} 100% {transform:scale(1.6); opacity:0;} }
    @keyframes wlOrbit { to {transform:rotate(360deg);} }
    @keyframes wlBugR { 0% {transform:translateX(0) scale(1); opacity:0;} 15% {opacity:1;} 70% {opacity:1;} 100% {transform:translateX(92px) scale(.2); opacity:0;} }
    @keyframes wlBugL { 0% {transform:translateX(0) scale(1); opacity:0;} 15% {opacity:1;} 70% {opacity:1;} 100% {transform:translateX(-92px) scale(.2); opacity:0;} }
    @keyframes wlBeat { 0%,100% {transform:scale(1);} 50% {transform:scale(1.06);} }
    @keyframes wlNudge { 0%,100% {transform:translateX(0);} 50% {transform:translateX(7px);} }
    @keyframes wlGlow { 0%,100% {box-shadow:0 0 0 0 rgba(59,130,246,.45), 0 10px 24px rgba(37,99,235,.25);} 50% {box-shadow:0 0 0 10px rgba(59,130,246,0), 0 10px 24px rgba(37,99,235,.4);} }
    @keyframes wlTwinkle { 0%,100% {transform:scale(.3); opacity:.2;} 50% {transform:scale(1.15); opacity:1;} }

    .wl-hero { display:flex; flex-wrap:wrap; align-items:center; gap:20px; position:relative; overflow:hidden; color:#fff; border-radius:26px; padding:36px 42px; background:linear-gradient(120deg,#0b1220 0%,#1e3a8a 55%,#2563eb 100%); background-size:300% 300%; box-shadow:0 18px 44px rgba(30,58,138,.3); animation:wlUp .8s ease both, gradientShift 12s ease infinite; }
    .wl-left { flex:1 1 380px; position:relative; z-index:2; }
    .wl-right { flex:0 0 360px; max-width:100%; position:relative; z-index:2; }
    .wl-badge { display:inline-block; font-size:12px; font-weight:700; letter-spacing:2px; padding:6px 14px; border-radius:999px; background:rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.28); margin-bottom:16px; animation:wlUp .6s ease both; }
    .wl-title { font-size:46px; font-weight:800; letter-spacing:-1px; line-height:1.12; }
    .wl-w { display:inline-block; margin-right:12px; animation:wlUp .7s ease both; }
    .wl-wave { display:inline-block; transform-origin:70% 70%; animation:wlWave 2.2s 1s infinite; }
    .wl-sub { font-size:17px; color:#cfe0ff; margin-top:14px; max-width:520px; line-height:1.55; animation:wlUp .8s .5s ease both; }
    .wl-chips { margin-top:20px; }
    .wl-chip { display:inline-block; font-size:13px; font-weight:600; padding:6px 14px; border-radius:999px; margin:0 8px 8px 0; background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.24); animation:popIn .6s ease both; }
    .wl-by { margin-top:14px; font-size:15px; color:#dbeafe; animation:wlUp .8s .9s ease both; }
    .wl-by b { color:#ffffff; }

    .wl-h { font-size:26px; font-weight:800; color:#0f172a; margin:38px 0 6px 0; letter-spacing:-.4px; animation:wlUp .7s ease both; }
    .wl-h span { color:#2563eb; }
    .wl-hs { font-size:14px; color:#64748b; margin-bottom:16px; }

    .wl-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:16px; }
    .wl-card { background:#fff; border:1px solid #e2e8f0; border-radius:18px; padding:20px; box-shadow:0 4px 16px rgba(15,23,42,.06); transition:transform .25s ease, box-shadow .25s ease, border-color .25s ease; animation:wlUp .7s ease both; }
    .wl-card:hover { transform:translateY(-6px); box-shadow:0 16px 32px rgba(37,99,235,.18); border-color:#93c5fd; }
    .wl-ic { width:56px; height:56px; border-radius:16px; display:flex; align-items:center; justify-content:center; margin-bottom:12px; transition:transform .25s ease; }
    .wl-card:hover .wl-ic { transform:scale(1.12) rotate(-6deg); }
    .wl-ic svg { width:32px; height:32px; }
    .wl-ct { font-size:17px; font-weight:700; color:#0f172a; margin-bottom:4px; }
    .wl-cx { font-size:13.5px; color:#64748b; line-height:1.55; }
    .ic-blue { background:#dbeafe; } .ic-green { background:#dcfce7; } .ic-purple { background:#ede9fe; } .ic-orange { background:#ffedd5; } .ic-pink { background:#fce7f3; }

    .wl-stat { background:linear-gradient(135deg,#ffffff,#f1f5f9); border:1px solid #e2e8f0; border-radius:16px; padding:16px 18px; animation:wlUp .7s ease both; transition:transform .25s ease; }
    .wl-stat:hover { transform:translateY(-4px); }
    .wl-sl { font-size:11px; font-weight:700; letter-spacing:1.2px; text-transform:uppercase; color:#64748b; }
    .wl-sv { font-size:18px; font-weight:800; color:#0f172a; margin-top:4px; }

    .wl-steps { display:flex; flex-wrap:wrap; align-items:stretch; gap:12px; }
    .wl-step { flex:1 1 220px; position:relative; background:#fff; border:1px solid #e2e8f0; border-radius:18px; padding:22px 20px 20px 20px; box-shadow:0 4px 16px rgba(15,23,42,.06); animation:wlUp .7s ease both; transition:transform .25s ease; }
    .wl-step:hover { transform:translateY(-5px); }
    .wl-num { position:absolute; top:-12px; left:18px; width:28px; height:28px; border-radius:50%; background:linear-gradient(135deg,#3b82f6,#1d4ed8); color:#fff; font-weight:800; font-size:14px; display:flex; align-items:center; justify-content:center; box-shadow:0 4px 10px rgba(37,99,235,.4); }
    .wl-arrow { align-self:center; font-size:30px; font-weight:800; color:#3b82f6; animation:wlNudge 1.4s ease-in-out infinite; }

    .wl-team { display:flex; flex-wrap:wrap; gap:20px; justify-content:center; }
    .wl-member { width:270px; text-align:center; background:#fff; border:1px solid #e2e8f0; border-radius:24px; padding:26px 22px; box-shadow:0 6px 20px rgba(15,23,42,.07); position:relative; overflow:hidden; animation:wlUp .8s ease both; transition:transform .25s ease, box-shadow .25s ease; }
    .wl-member::before { content:''; position:absolute; left:0; right:0; top:0; height:6px; background:linear-gradient(90deg,#3b82f6,#8b5cf6,#ec4899); }
    .wl-member:hover { transform:translateY(-8px); box-shadow:0 20px 38px rgba(99,102,241,.25); }
    .wl-ring { width:120px; height:120px; margin:6px auto 14px auto; padding:4px; border-radius:50%; background:conic-gradient(#3b82f6,#8b5cf6,#ec4899,#3b82f6); animation:wlGlow 2.6s ease-in-out infinite, mgFloat 3.4s ease-in-out infinite; }
    .wl-ring svg { width:100%; height:100%; border-radius:50%; display:block; background:#fff; }
    .wl-name { font-size:21px; font-weight:800; color:#0f172a; }
    .wl-role { font-size:13px; color:#64748b; margin-top:4px; }
    .wl-tag { display:inline-block; margin-top:12px; font-size:12px; font-weight:700; color:#1d4ed8; background:#dbeafe; padding:4px 12px; border-radius:999px; }

    .wl-cta { text-align:center; margin:34px 0 6px 0; font-size:15px; color:#475569; animation:wlUp .8s ease both; }
    .wl-orbit { transform-origin:180px 140px; animation:wlOrbit 16s linear infinite; }
    .wl-pulse { transform-box:fill-box; transform-origin:center; animation:wlPulse 3s ease-out infinite; }
    .wl-pulse.p2 { animation-delay:1.5s; }
    .wl-shield { transform-box:fill-box; transform-origin:center; animation:wlBeat 2.4s ease-in-out infinite; }
    .wl-bugr { transform-box:fill-box; transform-origin:center; animation:wlBugR 3.2s ease-in infinite; }
    .wl-bugl { transform-box:fill-box; transform-origin:center; animation:wlBugL 3.2s ease-in infinite; }
    .wl-star { transform-box:fill-box; transform-origin:center; animation:wlTwinkle 1.8s ease-in-out infinite; }
    @media (max-width: 760px) { .wl-title { font-size:34px; } .wl-hero { padding:26px 22px; } .wl-arrow { display:none; } }

    /* ---------- Greeting fonts ---------- */
    .wl-title { font-family:'Inter', sans-serif; font-size:44px; font-weight:800; letter-spacing:-1.2px; line-height:1.12; text-shadow:0 4px 18px rgba(0,0,0,.25); }
    .wl-title .grad { background:linear-gradient(90deg,#ffffff,#93c5fd,#fde68a,#ffffff); background-size:200% auto; -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; animation:wlUp .7s ease both, shimmer 5s linear infinite; }
    .wl-by { font-family:'Dancing Script', cursive; font-size:30px; font-weight:700; color:#dbeafe; margin-top:12px; letter-spacing:.5px; }
    .wl-by b { color:#fde68a; font-weight:700; }
    .wl-by .dot { color:#93c5fd; margin:0 10px; }
    @media (max-width: 760px) { .wl-title { font-size:32px; } .wl-by { font-size:25px; } }

    /* ---------- Names on the second page (same style as greeting) ---------- */
    .hero-credit { font-family:'Dancing Script', cursive; font-size:28px; font-weight:700; color:#dbeafe; margin-top:14px; letter-spacing:.5px; }
    .hero-credit b { color:#fde68a; font-weight:700; }
    .hero-credit .dot { color:#93c5fd; margin:0 10px; }

    /* ---------- Welcome page: greeting + title + team ---------- */
    @keyframes wlBlink { 0%,92%,100% {transform:scaleY(1);} 96% {transform:scaleY(.08);} }
    .blink { transform-box:fill-box; transform-origin:center; animation:wlBlink 4s infinite; }
    .wl-hi { font-family:'Dancing Script', cursive; font-size:42px; font-weight:700; color:#fde68a; line-height:1.1; text-shadow:0 3px 14px rgba(0,0,0,.25); }
    .wl-brand { display:flex; align-items:center; gap:14px; margin-top:4px; flex-wrap:wrap; }
    .wl-brand-ic { font-size:54px; display:inline-block; animation:mgFloat 3s ease-in-out infinite; }
    .wl-brand-t { font-family:'Inter', sans-serif; font-size:64px; font-weight:800; letter-spacing:-2px; line-height:1.05; background:linear-gradient(90deg,#ffffff,#93c5fd,#fde68a,#ffffff); background-size:200% auto; -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent; animation:wlUp .8s .5s ease both, shimmer 5s linear infinite; filter:drop-shadow(0 4px 14px rgba(0,0,0,.3)); }
    .wl-fl { position:absolute; font-size:22px; animation:mgFloat 3s ease-in-out infinite; }
    .wl-h { font-family:'Inter', sans-serif; }
    .wl-name { font-family:'Dancing Script', cursive; font-size:32px; }
    .wl-hero { padding:38px 46px; }
    @media (max-width: 760px) { .wl-hi { font-size:32px; } .wl-brand-t { font-size:40px; } .wl-brand-ic { font-size:38px; } }

    /* ---------- Bigger team photos ---------- */
    .wl-ring { width:160px; height:160px; }
    .wl-member { width:300px; padding:30px 24px; }
    .wl-name { font-size:36px; }

    /* ---------- LinkedIn-style profile cards ---------- */
    .wl-fl { display:none; }
    .wl-member { width:300px; padding:0 24px 28px 24px; border-radius:14px; border:1px solid #e2e8f0; box-shadow:0 4px 14px rgba(15,23,42,.07); overflow:hidden; }
    .wl-member::before { left:0; right:0; top:0; height:88px; background:linear-gradient(120deg,#0b1220 0%,#1e3a8a 55%,#2563eb 100%); }
    .wl-member:hover { transform:translateY(-4px); box-shadow:0 14px 28px rgba(30,58,138,.16); }
    .wl-ring { position:relative; z-index:2; width:116px; height:116px; margin:32px auto 14px auto; padding:4px; background:#ffffff; border-radius:50%; box-shadow:0 4px 14px rgba(15,23,42,.18); animation:none; }
    .wl-ring svg, .wl-ring img { border:none; }
    .wl-name { font-family:'Inter', sans-serif; font-size:22px; font-weight:700; letter-spacing:-.2px; color:#0f172a; }
    .wl-role { font-size:14px; font-weight:500; color:#475569; margin-top:2px; }
    .wl-tag { background:#eff6ff; color:#1e3a8a; border:1px solid #bfdbfe; font-weight:600; margin-top:14px; }

    /* ---------- Website background ---------- */
    .stApp {
        background:
            radial-gradient(circle at 10% 6%, rgba(147,197,253,.50), transparent 42%),
            radial-gradient(circle at 92% 10%, rgba(196,181,253,.38), transparent 40%),
            radial-gradient(circle at 85% 92%, rgba(125,211,252,.38), transparent 45%),
            radial-gradient(circle at 8% 88%, rgba(165,180,252,.30), transparent 42%),
            linear-gradient(160deg, #eef4ff 0%, #f8fbff 50%, #e8f0ff 100%);
        background-attachment: fixed;
    }
    [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: transparent; }

    /* ============================================================
       FULL-PAGE SCAM ALERT / NOT-SPAM HIGHLIGHT (2nd page)
       ============================================================ */
    @keyframes mgFxPulse { 0% {opacity:0;} 6% {opacity:1;} 20% {opacity:.35;} 34% {opacity:1;} 48% {opacity:.35;} 62% {opacity:1;} 100% {opacity:0;} }
    @keyframes mgFxGlow { 0% {opacity:0;} 10% {opacity:1;} 80% {opacity:1;} 100% {opacity:0;} }
    @keyframes mgBannerIn { 0% {opacity:0; transform:translate(-50%,-80px) scale(.8);} 60% {transform:translate(-50%,8px) scale(1.04);} 100% {opacity:1; transform:translate(-50%,0) scale(1);} }
    @keyframes mgBannerShake { 0%,100% {margin-left:0;} 15% {margin-left:-12px;} 30% {margin-left:10px;} 45% {margin-left:-8px;} 60% {margin-left:6px;} 75% {margin-left:-3px;} }
    @keyframes mgSiren { 0%,100% {transform:scale(1) rotate(0);} 25% {transform:scale(1.25) rotate(-12deg);} 75% {transform:scale(1.25) rotate(12deg);} }

    .mg-page-fx { position:fixed; inset:0; z-index:9998; pointer-events:none; opacity:0; }
    .mg-page-fx.spam { background:radial-gradient(ellipse at center, rgba(239,68,68,0) 45%, rgba(239,68,68,.30) 100%); box-shadow:inset 0 0 0 8px #ef4444, inset 0 0 140px 30px rgba(239,68,68,.65); animation:mgFxPulse 8s ease both; }
    .mg-page-fx.ham  { background:radial-gradient(ellipse at center, rgba(34,197,94,0) 45%, rgba(34,197,94,.26) 100%); box-shadow:inset 0 0 0 8px #22c55e, inset 0 0 140px 30px rgba(34,197,94,.55); animation:mgFxGlow 8s ease both; }

    .mg-banner { position:fixed; top:16px; left:50%; transform:translateX(-50%); z-index:9999; display:flex; align-items:center; gap:14px; padding:14px 22px 14px 26px; border-radius:999px; color:#ffffff; font-family:'Inter', sans-serif; font-weight:800; font-size:19px; letter-spacing:.3px; white-space:nowrap; max-width:94vw; transition:opacity .5s ease, top .5s ease; }
    .mg-banner.spam { background:linear-gradient(135deg,#991b1b,#ef4444); box-shadow:0 0 0 4px rgba(255,255,255,.85), 0 14px 40px rgba(239,68,68,.65); animation:mgBannerIn .6s ease both, mgBannerShake .6s .6s ease both; }
    .mg-banner.ham  { background:linear-gradient(135deg,#047857,#22c55e); box-shadow:0 0 0 4px rgba(255,255,255,.85), 0 14px 40px rgba(34,197,94,.55); animation:mgBannerIn .6s ease both; }
    .mg-banner.mg-out { opacity:0; top:-80px; }
    .mg-banner .mg-bi { font-size:28px; display:inline-block; }
    .mg-banner.spam .mg-bi { animation:mgSiren .8s ease-in-out infinite; }
    .mg-banner .mg-x { cursor:pointer; margin-left:6px; width:28px; height:28px; border-radius:50%; background:rgba(255,255,255,.25); display:flex; align-items:center; justify-content:center; font-size:14px; }
    .mg-banner .mg-x:hover { background:rgba(255,255,255,.45); }

    .stApp { transition:background .6s ease; }
    .stApp.mg-tint-spam { background:linear-gradient(135deg,#fee2e2 0%,#fff1f2 55%,#fecaca 100%) !important; }
    .stApp.mg-tint-ham  { background:linear-gradient(135deg,#dcfce7 0%,#f0fdf4 55%,#bbf7d0 100%) !important; }
    @media (max-width: 700px) { .mg-banner { font-size:14px; padding:10px 16px; white-space:normal; } }
    </style>
    """
)


# ============================================================
# NAVIGATION PAGES
# ============================================================

pages = [
    st.Page(
        "views/analyzer.py",
        title="Email Analyzer",
        icon=":material/mail:",
        default=True,
    ),
    st.Page(
        "views/evaluation.py",
        title="Model Evaluation",
        icon=":material/analytics:",
    ),
    st.Page(
        "views/monitoring.py",
        title="Monitoring",
        icon=":material/monitor_heart:",
    ),
    st.Page(
        "views/model_info.py",
        title="Model Information",
        icon=":material/info:",
    ),
]


# ============================================================
# LOAD MODEL AND SERVICES
# ============================================================

get_service()

model, model_error = get_model_bundle()

# Welcome page is shown first on every new visit
if "welcomed" not in st.session_state:
    st.session_state["welcomed"] = False


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    html(
        """
        <div class="brand">
            <div class="brand-logo">🛡️</div>
            <div class="brand-name">MailGuard ML</div>
            <div class="brand-tag">AI Email Security System</div>
        </div>
        """
    )

    # Live scanner slideshow (changes when you click "Analyze")
    html(
        """
        <div class="side-card">
            <div class="side-card-title">Live Scanner</div>
            <div class="mg-stage" data-scene="idle">

                <div class="mg-sl sl-i1">
                    <svg viewBox="0 0 240 150">
                        <g class="g-float"><rect x="62" y="48" width="116" height="76" rx="10" fill="#f8fafc"/><path d="M62 58 L120 102 L178 58" fill="none" stroke="#60a5fa" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/><rect class="g-laser" x="54" y="46" width="132" height="4" rx="2" fill="#38bdf8"/></g>
                        <circle class="g-dot d1" cx="30" cy="40" r="4" fill="#93c5fd"/>
                        <circle class="g-dot d2" cx="206" cy="108" r="5" fill="#bfdbfe"/>
                        <circle class="g-dot d3" cx="44" cy="120" r="3" fill="#60a5fa"/>
                        <text x="120" y="22" text-anchor="middle" fill="#bfdbfe" font-size="11" font-weight="700" letter-spacing="2">SCANNING INBOX</text>
                    </svg>
                </div>

                <div class="mg-sl sl-i2">
                    <svg viewBox="0 0 240 150">
                        <circle class="g-ring" cx="120" cy="78" r="58" fill="none" stroke="#60a5fa" stroke-width="2" stroke-dasharray="6 8"/>
                        <path class="g-shield" d="M120 28 L168 46 V80 C168 106 144 122 120 130 C96 122 72 106 72 80 V46 Z" fill="#2563eb" stroke="#93c5fd" stroke-width="3"/>
                        <path class="g-tick" d="M98 78 L114 94 L144 62" fill="none" stroke="#ffffff" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
                        <text x="120" y="146" text-anchor="middle" fill="#bfdbfe" font-size="11" font-weight="700" letter-spacing="2">AI PROTECTION</text>
                    </svg>
                </div>

                <div class="mg-sl sl-i3">
                    <svg viewBox="0 0 240 150">
                        <g class="g-bob b1"><rect x="20" y="62" width="58" height="40" rx="6" fill="#f8fafc"/><path d="M20 68 L49 88 L78 68" fill="none" stroke="#60a5fa" stroke-width="3" stroke-linecap="round"/><circle cx="76" cy="62" r="10" fill="#22c55e"/><path d="M71 62 L75 66 L82 57" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></g>
                        <g class="g-bob b2"><rect x="91" y="50" width="58" height="40" rx="6" fill="#f8fafc"/><path d="M91 56 L120 76 L149 56" fill="none" stroke="#60a5fa" stroke-width="3" stroke-linecap="round"/><circle cx="147" cy="50" r="10" fill="#22c55e"/><path d="M142 50 L146 54 L153 45" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></g>
                        <g class="g-bob b3"><rect x="162" y="62" width="58" height="40" rx="6" fill="#f8fafc"/><path d="M162 68 L191 88 L220 68" fill="none" stroke="#60a5fa" stroke-width="3" stroke-linecap="round"/><circle cx="218" cy="62" r="10" fill="#ef4444"/><path d="M213 57 L223 67 M223 57 L213 67" stroke="#fff" stroke-width="3" stroke-linecap="round"/></g>
                        <text x="120" y="130" text-anchor="middle" fill="#bfdbfe" font-size="11" font-weight="700" letter-spacing="2">SORTING MAIL</text>
                    </svg>
                </div>

                <div class="mg-sl sl-scan">
                    <svg viewBox="0 0 240 150">
                        <g class="g-float"><rect x="62" y="52" width="116" height="72" rx="10" fill="#f8fafc"/><path d="M62 62 L120 104 L178 62" fill="none" stroke="#60a5fa" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/></g>
                        <g class="g-orbit"><circle cx="120" cy="30" r="15" fill="rgba(56,189,248,0.25)" stroke="#38bdf8" stroke-width="4"/><path d="M131 41 L142 52" stroke="#38bdf8" stroke-width="5" stroke-linecap="round"/></g>
                        <circle class="g-dot d1" cx="108" cy="141" r="3.5" fill="#bae6fd"/>
                        <circle class="g-dot d2" cx="120" cy="141" r="3.5" fill="#bae6fd"/>
                        <circle class="g-dot d3" cx="132" cy="141" r="3.5" fill="#bae6fd"/>
                    </svg>
                </div>

                <div class="mg-sl sl-spam">
                    <svg viewBox="0 0 240 150">
                        <circle class="g-wave" cx="120" cy="88" r="40" fill="none" stroke="#fca5a5" stroke-width="3"/>
                        <circle class="g-wave w2" cx="120" cy="88" r="40" fill="none" stroke="#fca5a5" stroke-width="3"/>
                        <g class="g-shake"><rect x="62" y="50" width="116" height="76" rx="10" fill="#fff1f2" stroke="#ef4444" stroke-width="3"/><path d="M62 60 L120 104 L178 60" fill="none" stroke="#ef4444" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/><g class="g-warn"><path d="M120 62 L146 106 H94 Z" fill="#f59e0b" stroke="#7f1d1d" stroke-width="3" stroke-linejoin="round"/><rect x="117.5" y="76" width="5" height="16" rx="2.5" fill="#7f1d1d"/><circle cx="120" cy="99" r="3" fill="#7f1d1d"/></g></g>
                        <text class="g-bug a1" x="22" y="56" font-size="24">🦠</text>
                        <text class="g-bug a2" x="196" y="64" font-size="22">☠️</text>
                        <text class="g-bug a3" x="198" y="132" font-size="22">🚫</text>
                        <g class="g-stamp"><rect x="14" y="12" width="82" height="28" rx="6" fill="#dc2626" stroke="#ffffff" stroke-width="3"/><text x="55" y="32" text-anchor="middle" fill="#ffffff" font-size="17" font-weight="800" letter-spacing="2">SPAM</text></g>
                    </svg>
                </div>

                <div class="mg-sl sl-ham">
                    <svg viewBox="0 0 240 150">
                        <circle class="g-wave" cx="120" cy="88" r="40" fill="none" stroke="#86efac" stroke-width="3"/>
                        <circle class="g-wave w2" cx="120" cy="88" r="40" fill="none" stroke="#86efac" stroke-width="3"/>
                        <g class="g-float"><rect x="62" y="50" width="116" height="76" rx="10" fill="#f0fdf4" stroke="#22c55e" stroke-width="3"/><path d="M62 60 L120 104 L178 60" fill="none" stroke="#22c55e" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/></g>
                        <circle class="g-okc" cx="120" cy="86" r="26" fill="#16a34a" stroke="#ffffff" stroke-width="4"/>
                        <path class="g-oktick" d="M107 86 L116 95 L134 76" fill="none" stroke="#ffffff" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
                        <polygon class="g-star s1" points="40,38 43,47 52,50 43,53 40,62 37,53 28,50 37,47" fill="#fde68a"/>
                        <polygon class="g-star s2" points="204,34 206,41 213,43 206,45 204,52 202,45 195,43 202,41" fill="#fde68a"/>
                        <polygon class="g-star s3" points="208,112 210,119 217,121 210,123 208,130 206,123 199,121 206,119" fill="#ffffff"/>
                        <polygon class="g-star s4" points="34,112 36,119 43,121 36,123 34,130 32,123 25,121 32,119" fill="#ffffff"/>
                        <g class="g-stamp"><rect x="150" y="12" width="76" height="28" rx="6" fill="#16a34a" stroke="#ffffff" stroke-width="3"/><text x="188" y="32" text-anchor="middle" fill="#ffffff" font-size="17" font-weight="800" letter-spacing="2">SAFE</text></g>
                    </svg>
                </div>

            </div>
            <div class="mg-cap" data-scene="idle">Ready to scan</div>
        </div>
        """
    )

    # Model status
    if model is not None:
        html(
            f"""
            <div class="side-card">
                <div class="side-card-title">Model Status</div>
                <div class="side-row"><span class="dot dot-green"></span>Ready</div>
                <div class="side-row">{model.display_name} v{model.version}</div>
            </div>
            """
        )
    else:
        html(
            """
            <div class="side-card">
                <div class="side-card-title">Model Status</div>
                <div class="side-row"><span class="dot dot-red"></span>Model unavailable</div>
            </div>
            """
        )

    # Team
    html(
        """
        <div class="side-card">
            <div class="side-card-title">Project Team</div>
            <div class="side-row"><span class="avatar">K</span><b>Keerthi</b></div>
            <div class="side-row"><span class="avatar">N</span><b>Nandini</b></div>
        </div>
        """
    )

    if st.session_state["welcomed"]:
        if st.button("🏠  Welcome page", key="show_welcome", use_container_width=True):
            st.session_state["welcomed"] = False
            st.rerun()

    st.markdown("---")

    st.caption(
        "Educational spam-detection demo trained on the "
        "public SpamAssassin corpus. Emails are processed "
        "in memory and are not stored or logged."
    )


# ============================================================
# WELCOME PAGE (first screen when the website opens)
# ============================================================

def show_welcome() -> None:
    hero_illustration = """
    <svg viewBox="0 0 360 280">
        <circle class="wl-pulse" cx="180" cy="140" r="90" fill="rgba(255,255,255,0.10)"/>
        <circle class="wl-pulse p2" cx="180" cy="140" r="90" fill="rgba(255,255,255,0.10)"/>
        <circle cx="180" cy="140" r="104" fill="none" stroke="rgba(255,255,255,0.28)" stroke-width="2" stroke-dasharray="6 9"/>
        <g class="wl-orbit">
            <g transform="translate(180 36)"><rect x="-22" y="-15" width="44" height="30" rx="5" fill="#f8fafc"/><path d="M-22 -9 L0 6 L22 -9" fill="none" stroke="#60a5fa" stroke-width="3" stroke-linejoin="round"/></g>
            <g transform="translate(284 140)"><rect x="-22" y="-15" width="44" height="30" rx="5" fill="#f8fafc"/><path d="M-22 -9 L0 6 L22 -9" fill="none" stroke="#60a5fa" stroke-width="3" stroke-linejoin="round"/></g>
            <g transform="translate(180 244)"><rect x="-22" y="-15" width="44" height="30" rx="5" fill="#f8fafc"/><path d="M-22 -9 L0 6 L22 -9" fill="none" stroke="#60a5fa" stroke-width="3" stroke-linejoin="round"/></g>
            <g transform="translate(76 140)"><rect x="-22" y="-15" width="44" height="30" rx="5" fill="#f8fafc"/><path d="M-22 -9 L0 6 L22 -9" fill="none" stroke="#60a5fa" stroke-width="3" stroke-linejoin="round"/></g>
        </g>
        <path class="wl-shield" d="M180 78 L236 100 V144 C236 176 208 196 180 206 C152 196 124 176 124 144 V100 Z" fill="#2563eb" stroke="#bfdbfe" stroke-width="4"/>
        <path d="M156 142 L174 160 L208 122" fill="none" stroke="#ffffff" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
        <text class="wl-bugr" x="12" y="96" font-size="26">🦠</text>
        <text class="wl-bugr" x="12" y="200" font-size="24" style="animation-delay:1.4s">🚫</text>
        <text class="wl-bugl" x="326" y="110" font-size="26" style="animation-delay:.7s">☠️</text>
        <text class="wl-bugl" x="326" y="214" font-size="24" style="animation-delay:2s">⚠️</text>
        <polygon class="wl-star" points="60,40 63,49 72,52 63,55 60,64 57,55 48,52 57,49" fill="#fde68a"/>
        <polygon class="wl-star" style="animation-delay:.6s" points="306,44 308,51 315,53 308,55 306,62 304,55 297,53 304,51" fill="#ffffff"/>
        <polygon class="wl-star" style="animation-delay:1.1s" points="300,246 302,253 309,255 302,257 300,264 298,257 291,255 298,253" fill="#fde68a"/>
    </svg>
    """

    # Clean LinkedIn-style initials badges (used when no photo is found in assets/)
    avatar_keerthi = """
    <svg viewBox="0 0 200 200">
        <defs>
            <linearGradient id="kbg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1e3a8a"/><stop offset="1" stop-color="#2563eb"/></linearGradient>
        </defs>
        <rect width="200" height="200" fill="url(#kbg)"/>
        <text x="100" y="100" text-anchor="middle" dominant-baseline="central" fill="#ffffff" font-family="Inter, Arial, sans-serif" font-size="84" font-weight="700" letter-spacing="2">K</text>
    </svg>
    """

    avatar_nandini = """
    <svg viewBox="0 0 200 200">
        <defs>
            <linearGradient id="nbg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0f766e"/><stop offset="1" stop-color="#0ea5a4"/></linearGradient>
        </defs>
        <rect width="200" height="200" fill="url(#nbg)"/>
        <text x="100" y="100" text-anchor="middle" dominant-baseline="central" fill="#ffffff" font-family="Inter, Arial, sans-serif" font-size="84" font-weight="700" letter-spacing="2">N</text>
    </svg>
    """

    def photo_or_avatar(name: str, fallback_svg: str) -> str:
        """Use assets/<name>.(jpg|jpeg|png|webp) if it exists, otherwise the drawn avatar."""
        folder = pathlib.Path(__file__).parent / "assets"
        for ext in ("jpg", "jpeg", "png", "webp"):
            path = folder / f"{name}.{ext}"
            if path.exists():
                mime = "jpeg" if ext in ("jpg", "jpeg") else ext
                data = base64.b64encode(path.read_bytes()).decode()
                return (
                    f'<img src="data:image/{mime};base64,{data}" alt="{name}" '
                    'style="width:100%;height:100%;object-fit:cover;border-radius:50%;display:block"/>'
                )
        return fallback_svg

    page = """
    <div class="wl-hero">
        <span class="orb orb1"></span>
        <span class="orb orb2"></span>
        <div class="wl-left">
            <div class="wl-hi">
                <span class="wl-w" style="animation-delay:.1s">Hi,</span><span class="wl-w wl-wave" style="animation-delay:.25s">👋</span>
                <span class="wl-w" style="animation-delay:.4s">welcome to</span>
            </div>
            <div class="wl-brand">
                <span class="wl-brand-ic">🛡️</span><span class="wl-brand-t">MailGuard ML</span>
            </div>
            <div class="wl-by">Developed by <b>Keerthi</b><span class="dot">•</span><b>Nandini</b></div>
        </div>
        <div class="wl-right">__HERO__</div>
    </div>

    <div class="wl-h" style="text-align:center">Meet the <span>team</span></div>
    <div class="wl-hs" style="text-align:center">The people who built MailGuard ML.</div>
    <div class="wl-team">
        <div class="wl-member" style="animation-delay:.1s">
            <span class="wl-fl" style="top:16px; left:18px">💻</span>
            <span class="wl-fl" style="top:18px; right:20px; animation-delay:-1s">✨</span>
            <div class="wl-ring">__AV1__</div>
            <div class="wl-name">Keerthi</div>
            <div class="wl-role">Project Developer</div>
            <div class="wl-tag">Team Member 01</div>
        </div>
        <div class="wl-member" style="animation-delay:.3s">
            <span class="wl-fl" style="top:16px; left:18px; animation-delay:-.6s">🚀</span>
            <span class="wl-fl" style="top:18px; right:20px; animation-delay:-1.6s">⭐</span>
            <div class="wl-ring">__AV2__</div>
            <div class="wl-name">Nandini</div>
            <div class="wl-role">Project Developer</div>
            <div class="wl-tag">Team Member 02</div>
        </div>
    </div>

    <div class="wl-cta">Ready to check your first email? 👇</div>
    """

    for key, val in {
        "__HERO__": hero_illustration,
        "__AV1__": photo_or_avatar("keerthi", avatar_keerthi),
        "__AV2__": photo_or_avatar("nandini", avatar_nandini),
    }.items():
        page = page.replace(key, val)

    html(page)

    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        if st.button("🚀  Get Started", type="primary", use_container_width=True, key="get_started"):
            st.session_state["welcomed"] = True
            st.rerun()

    html(
        """
        <div class="footer">
            🛡️ <b>MailGuard ML</b> &nbsp;|&nbsp; Developed by Keerthi &amp; Nandini
        </div>
        """
    )


if not st.session_state["welcomed"]:
    show_welcome()
    st.stop()


# ============================================================
# HERO BANNER (shown above every page)
# ============================================================

html(
    """
    <div class="hero">
        <span class="orb orb1"></span>
        <span class="orb orb2"></span>
        <div class="hero-title-row">
            <span class="hero-emoji">🛡️</span>
            <span class="hero-title">MailGuard ML</span>
        </div>
        <div class="hero-subtitle">
            AI-powered email classification and spam detection
        </div>
        <div class="chips">
            <span class="chip">📧 Email Analysis</span>
            <span class="chip">🤖 ML Detection</span>
            <span class="chip">📊 Model Insights</span>
        </div>
        <div class="hero-credit">
            Developed by <b>Keerthi</b><span class="dot">•</span><b>Nandini</b>
        </div>
    </div>
    """
)


# ============================================================
# ACTIVE PAGE
# ============================================================

st.navigation(pages).run()


# ============================================================
# CONTROLLER: alert effects + slideshow scene switching
#   idle (auto slideshow) -> click "Analyze" -> scan -> spam / ham
# ============================================================

components.html(
    r"""
    <script>
    (function () {
        const p = window.parent;
        const d = p.document;
        if (p.__mgv3) { return; }
        p.__mgv3 = true;

        const colors = ['#bbf7d0', '#fde68a', '#bfdbfe', '#fbcfe8', '#a7f3d0', '#ffffff'];
        const CAP = { idle: 'Ready to scan', scan: 'Scanning email...', spam: 'Spam detected!', ham: 'Email is safe' };
        let scene = 'idle', scanStart = 0, poll = null, resetT = null;

        function applyScene() {
            const st = d.querySelector('.mg-stage');
            if (st && st.getAttribute('data-scene') !== scene) { st.setAttribute('data-scene', scene); }
            const cap = d.querySelector('.mg-cap');
            if (cap) {
                if (cap.getAttribute('data-scene') !== scene) { cap.setAttribute('data-scene', scene); }
                if (cap.textContent !== CAP[scene]) { cap.textContent = CAP[scene]; }
            }
        }
        function setScene(s) { scene = s; applyScene(); }

        function classify(text) {
            const t = text.toLowerCase();
            if (/not spam|not-spam|legitimate|\bham\b|\bsafe\b/.test(t)) return 'ham';
            if (/spam|phishing|malicious|suspicious/.test(t)) return 'spam';
            return null;
        }

        function burst(el) {
            for (let i = 0; i < 30; i++) {
                const s = d.createElement('i');
                s.className = 'mg-cf';
                s.style.left = Math.floor(Math.random() * 98) + '%';
                s.style.background = colors[Math.floor(Math.random() * colors.length)];
                s.style.animationDelay = (Math.random() * 1.2).toFixed(2) + 's';
                el.appendChild(s);
                setTimeout(function () { s.remove(); }, 4500);
            }
        }

        function scanAlerts() {
            d.querySelectorAll('div[data-testid="stAlert"]:not([data-mg])').forEach(function (el) {
                el.setAttribute('data-mg', '1');
                const kind = classify(el.innerText || '');
                if (!kind) return;
                el.classList.add('mg-' + kind);
                if (kind === 'ham') burst(el);
            });
        }

        function detectResult() {
            const main = d.querySelector('[data-testid="stMain"]') || d.body;
            if (main.querySelector('.vd-card.vd-spam')) return 'spam';
            if (main.querySelector('.vd-card.vd-ham')) return 'ham';
            const nodes = main.querySelectorAll('[data-testid="stAlert"], [data-testid="stMetricValue"], [data-testid="stMarkdownContainer"]');
            for (const n of nodes) {
                if (n.querySelector('.hero, .footer, .vd-card')) continue;
                const t = (n.innerText || '').trim().toLowerCase();
                if (!t || t.length > 300) continue;
                if (/\bnot spam\b|\bnot-spam\b|\blegitimate\b|^ham$|looks safe|is safe/.test(t)) return 'ham';
                if (/spam detected|is spam|likely spam|classified as spam|phishing|^spam$/.test(t)) return 'spam';
            }
            return null;
        }

        let fxId = 0;
        function showPageFx(kind) {
            const id = ++fxId;
            d.querySelectorAll('.mg-page-fx, .mg-banner').forEach(function (e) { e.remove(); });
            const app = d.querySelector('.stApp');
            if (app) { app.classList.remove('mg-tint-spam', 'mg-tint-ham'); app.classList.add('mg-tint-' + kind); }

            const fx = d.createElement('div');
            fx.className = 'mg-page-fx ' + kind;
            d.body.appendChild(fx);

            const bn = d.createElement('div');
            bn.className = 'mg-banner ' + kind;
            const ic = d.createElement('span');
            ic.className = 'mg-bi';
            ic.textContent = kind === 'spam' ? '\u{1F6A8}' : '\u2705';
            const tx = d.createElement('span');
            tx.textContent = kind === 'spam' ? 'SCAM ALERT \u2014 This email is SPAM' : 'NOT SPAM \u2014 This email is safe';
            const x = d.createElement('span');
            x.className = 'mg-x';
            x.textContent = '\u2715';
            bn.appendChild(ic); bn.appendChild(tx); bn.appendChild(x);
            d.body.appendChild(bn);

            function close() {
                if (id !== fxId) return;
                fx.remove();
                bn.classList.add('mg-out');
                setTimeout(function () { bn.remove(); }, 600);
                if (app) { app.classList.remove('mg-tint-' + kind); }
            }
            x.addEventListener('click', close);
            setTimeout(close, 9000);
        }

        function finish(r) {
            clearInterval(poll);
            setScene(r);
            showPageFx(r);
            clearTimeout(resetT);
            resetT = setTimeout(function () { setScene('idle'); }, 15000);
        }

        function startScan() {
            clearTimeout(resetT);
            clearInterval(poll);
            setScene('scan');
            scanStart = Date.now();
            poll = setInterval(function () {
                const elapsed = Date.now() - scanStart;
                const running = !!d.querySelector('[data-testid="stStatusWidget"]');
                if (elapsed >= 1800 && !running) {
                    const r = detectResult();
                    if (r) { finish(r); return; }
                }
                if (elapsed > 20000) { clearInterval(poll); setScene('idle'); }
            }, 250);
        }

        d.addEventListener('click', function (e) {
            const b = e.target && e.target.closest ? e.target.closest('button') : null;
            if (!b) return;
            if (/analy[sz]e/i.test(b.innerText || '')) { startScan(); }
        }, true);

        new p.MutationObserver(function () { scanAlerts(); applyScene(); }).observe(d.body, { childList: true, subtree: true });
        scanAlerts();
        applyScene();
    })();
    </script>
    """,
    height=0,
)


# ============================================================
# FOOTER
# ============================================================

html(
    """
    <div class="footer">
        🛡️ <b>MailGuard ML</b> &nbsp;|&nbsp; AI Email Security &amp; Spam Detection
        <br>
        Developed by Keerthi &amp; Nandini
    </div>
    """
)