"""
OFFLINE MCP Terminal Clinet
"""
import html

import streamlit as st
import asyncio
import threading
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, AsyncGenerator
from pathlib import Path
import sqlite3
import hashlib
import time
import re
from collections import deque

from client import MCPAppClient
from agent import TerminalAgent
from config import AGENT_DEBUG_MODE

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="OFFLINE MCP Terminal Clinet",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 10/10 CHAMPIONSHIP CSS
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ═══════════════════════════════════════════════
   ROOT TOKENS
═══════════════════════════════════════════════ */
:root {
    --acid:        #c8ff57;
    --acid-glow:   rgba(200,255,87,0.18);
    --acid-border: rgba(200,255,87,0.28);
    --cyan:        #00e5ff;
    --cyan-glow:   rgba(0,229,255,0.14);
    --violet:      #b57bff;
    --orange:      #ff7a3d;

    --bg0: #05080f;
    --bg1: #090d18;
    --bg2: #0e1422;
    --bg3: rgba(255,255,255,0.04);
    --bg4: rgba(255,255,255,0.07);

    --border0: rgba(255,255,255,0.06);
    --border1: rgba(255,255,255,0.12);
    --border2: rgba(200,255,87,0.22);

    --text0: #f2f4f8;
    --text1: rgba(242,244,248,0.65);
    --text2: rgba(242,244,248,0.35);

    --r-sm: 10px;
    --r-md: 16px;
    --r-lg: 22px;
    --r-xl: 28px;
}

/* ═══════════════════════════════════════════════
   GLOBAL RESET & BASE
═══════════════════════════════════════════════ */
*, *::before, *::after { box-sizing: border-box; }

.stApp {
    background: var(--bg0);
    font-family: 'Inter', sans-serif;
    color: var(--text0);
    min-height: 100vh;
}

/* Animated noise grain overlay */
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.035'/%3E%3C/svg%3E");
    pointer-events: none;
    z-index: 0;
    opacity: 0.6;
}

#MainMenu, footer, header { visibility: hidden; }

/* ═══════════════════════════════════════════════
   SIDEBAR TOGGLE — ALWAYS VISIBLE
═══════════════════════════════════════════════ */
[data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    pointer-events: all !important;
    position: fixed !important;
    left: 0 !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    z-index: 9999999 !important;
    background: var(--acid) !important;
    border: none !important;
    border-radius: 0 12px 12px 0 !important;
    width: 24px !important;
    height: 64px !important;
    padding: 0 !important;
    cursor: pointer !important;
    box-shadow: 4px 0 28px rgba(200,255,87,0.55) !important;
    transition: width 0.2s ease, box-shadow 0.2s ease !important;
    align-items: center !important;
    justify-content: center !important;
}
[data-testid="collapsedControl"]:hover {
    width: 34px !important;
    box-shadow: 6px 0 40px rgba(200,255,87,0.85) !important;
}
[data-testid="collapsedControl"] svg {
    color: #05080f !important;
    fill: #05080f !important;
    width: 13px !important;
    height: 13px !important;
}

[data-testid="baseButton-header"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    background: rgba(200,255,87,0.1) !important;
    border: 1px solid var(--acid-border) !important;
    color: var(--acid) !important;
    border-radius: 8px !important;
    padding: 5px 9px !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}
[data-testid="baseButton-header"]:hover {
    background: rgba(200,255,87,0.2) !important;
    box-shadow: 0 0 18px rgba(200,255,87,0.3) !important;
}
[data-testid="baseButton-header"] svg {
    color: var(--acid) !important;
    fill: var(--acid) !important;
}

/* ═══════════════════════════════════════════════
   SIDEBAR SHELL
═══════════════════════════════════════════════ */
section[data-testid="stSidebar"] {
    background: var(--bg1) !important;
    border-right: 1px solid var(--border1) !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding: 0 !important;
}

/* ═══════════════════════════════════════════════
   SIDEBAR BRAND HEADER
═══════════════════════════════════════════════ */
.sb-header {
    padding: 22px 20px 18px;
    border-bottom: 1px solid var(--border0);
    background: linear-gradient(160deg, rgba(200,255,87,0.07) 0%, rgba(0,229,255,0.05) 100%);
    position: relative;
    overflow: hidden;
}
.sb-header::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--acid), transparent);
    opacity: 0.4;
}
.sb-logo-row {
    display: flex;
    align-items: center;
    gap: 12px;
}
.sb-logo-mark {
    width: 40px;
    height: 40px;
    background: var(--acid);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    box-shadow: 0 0 24px rgba(200,255,87,0.5);
    flex-shrink: 0;
    animation: logoPulse 3s ease-in-out infinite;
}
@keyframes logoPulse {
    0%,100% { box-shadow: 0 0 20px rgba(200,255,87,0.4); }
    50%      { box-shadow: 0 0 36px rgba(200,255,87,0.8); }
}
.sb-logo-text .name {
    font-family: 'Syne', sans-serif;
    font-size: 16px;
    font-weight: 800;
    color: var(--text0);
    letter-spacing: -0.3px;
    line-height: 1;
}
.sb-logo-text .tag {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: var(--acid);
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-top: 4px;
    opacity: 0.8;
}

/* ═══════════════════════════════════════════════
   SIDEBAR STATUS PILL
═══════════════════════════════════════════════ */
.sb-status-wrap {
    padding: 12px 20px;
    border-bottom: 1px solid var(--border0);
}
.sb-status-pill {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 9px 14px;
    border-radius: 50px;
    font-family: 'Fira Code', monospace;
    font-size: 11px;
    font-weight: 500;
}
.sb-status-pill.online {
    background: rgba(200,255,87,0.08);
    border: 1px solid rgba(200,255,87,0.25);
    color: var(--acid);
}
.sb-status-pill.connecting {
    background: rgba(255,170,0,0.08);
    border: 1px solid rgba(255,170,0,0.25);
    color: #ffaa00;
}
.sb-status-pill.offline {
    background: rgba(255,70,70,0.08);
    border: 1px solid rgba(255,70,70,0.25);
    color: #ff4646;
}
.dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
}
.online .dot  { background: var(--acid); box-shadow: 0 0 10px var(--acid); animation: blinkDot 2s infinite; }
.connecting .dot { background: #ffaa00; box-shadow: 0 0 10px #ffaa00; animation: blinkDot 0.8s infinite; }
.offline .dot { background: #ff4646; }
@keyframes blinkDot {
    0%,100% { opacity:1; transform:scale(1); }
    50%     { opacity:0.4; transform:scale(0.7); }
}
.pill-info { flex:1; }
.pill-label { font-weight: 700; font-size: 11px; letter-spacing: 0.5px; }
.pill-sub   { font-size: 9px; opacity: 0.65; margin-top: 2px; letter-spacing: 0.3px; }

/* ═══════════════════════════════════════════════
   SIDEBAR SECTION LABEL
═══════════════════════════════════════════════ */
.sb-section-label {
    padding: 14px 20px 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: var(--text2);
    display: flex;
    align-items: center;
    gap: 10px;
}
.sb-section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--border0);
}

/* ═══════════════════════════════════════════════
   SESSION BUTTONS IN SIDEBAR
═══════════════════════════════════════════════ */
.sb-pad { padding: 0 16px 12px; }

section[data-testid="stSidebar"] .stButton > button {
    background: var(--bg3) !important;
    color: var(--text1) !important;
    border: 1px solid var(--border1) !important;
    border-radius: var(--r-sm) !important;
    box-shadow: none !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    padding: 9px 12px !important;
    letter-spacing: 0.3px !important;
    text-transform: none !important;
    transition: all 0.18s ease !important;
    transform: none !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--acid-glow) !important;
    border-color: var(--acid-border) !important;
    color: var(--acid) !important;
    box-shadow: none !important;
    transform: none !important;
}

/* Session list item buttons */
.session-btn-wrap button {
    text-align: left !important;
    justify-content: flex-start !important;
}

/* ═══════════════════════════════════════════════
   TOOL / RESOURCE / PROMPT CARDS IN SIDEBAR
═══════════════════════════════════════════════ */
.sb-card {
    margin: 0 16px 6px;
    padding: 11px 14px;
    background: var(--bg3);
    border: 1px solid var(--border0);
    border-radius: var(--r-sm);
    transition: all 0.2s ease;
    cursor: default;
    position: relative;
    overflow: hidden;
}
.sb-card::before {
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    border-radius: 2px 0 0 2px;
    background: transparent;
    transition: background 0.2s;
}
.sb-card:hover {
    background: var(--bg4);
    border-color: var(--border1);
    transform: translateX(4px);
}
.sb-card:hover::before { background: var(--acid); }

.sb-card-top {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
}
.sb-card-icon {
    font-size: 14px;
    width: 22px;
    text-align: center;
    flex-shrink: 0;
}
.sb-card-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 500;
    color: var(--cyan);
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.sb-card-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    padding: 2px 7px;
    border-radius: 4px;
    font-weight: 600;
    letter-spacing: 0.5px;
    flex-shrink: 0;
}
.badge-t { background: rgba(200,255,87,0.12); color: var(--acid); border: 1px solid rgba(200,255,87,0.2); }
.badge-r { background: rgba(0,229,255,0.10); color: var(--cyan); border: 1px solid rgba(0,229,255,0.18); }
.badge-p { background: rgba(181,123,255,0.10); color: var(--violet); border: 1px solid rgba(181,123,255,0.18); }

.sb-card-desc {
    font-family: 'Manrope', sans-serif;
    font-size: 10.5px;
    color: var(--text2);
    line-height: 1.55;
    padding-left: 30px;
}

/* Category divider inside expanders */
.sb-cat {
    margin: 6px 16px 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--text2);
    padding-bottom: 4px;
    border-bottom: 1px dashed var(--border0);
}

/* ═══════════════════════════════════════════════
   EXPANDERS IN SIDEBAR
═══════════════════════════════════════════════ */
section[data-testid="stSidebar"] .streamlit-expanderHeader {
    background: var(--bg3) !important;
    border: 1px solid var(--border0) !important;
    border-radius: var(--r-sm) !important;
    margin: 0 16px 6px !important;
    padding: 10px 14px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    color: var(--text1) !important;
    letter-spacing: 0.3px !important;
    transition: all 0.18s !important;
}
section[data-testid="stSidebar"] .streamlit-expanderHeader:hover {
    background: var(--acid-glow) !important;
    border-color: var(--acid-border) !important;
    color: var(--acid) !important;
}
section[data-testid="stSidebar"] .streamlit-expanderContent {
    border: none !important;
    padding: 4px 0 8px !important;
}

/* ═══════════════════════════════════════════════
   SIDEBAR STATS MINI GRID
═══════════════════════════════════════════════ */
.sb-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    padding: 0 16px 16px;
}
.sb-stat {
    background: var(--bg3);
    border: 1px solid var(--border0);
    border-radius: var(--r-sm);
    padding: 10px 12px;
}
.sb-stat-val {
    font-family: 'Syne', sans-serif;
    font-size: 22px;
    font-weight: 800;
    color: var(--text0);
    line-height: 1;
}
.sb-stat-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    color: var(--text2);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 4px;
}

/* ═══════════════════════════════════════════════
   ALERTS IN SIDEBAR
═══════════════════════════════════════════════ */
section[data-testid="stSidebar"] .stSuccess,
section[data-testid="stSidebar"] .stSuccess > div {
    background: rgba(200,255,87,0.08) !important;
    border: 1px solid rgba(200,255,87,0.25) !important;
    color: var(--acid) !important;
    border-radius: var(--r-sm) !important;
}
section[data-testid="stSidebar"] .stWarning,
section[data-testid="stSidebar"] .stWarning > div {
    background: rgba(255,170,0,0.08) !important;
    border: 1px solid rgba(255,170,0,0.25) !important;
    color: #ffaa00 !important;
    border-radius: var(--r-sm) !important;
}
section[data-testid="stSidebar"] .stError,
section[data-testid="stSidebar"] .stError > div {
    background: rgba(255,70,70,0.08) !important;
    border: 1px solid rgba(255,70,70,0.25) !important;
    color: #ff4646 !important;
    border-radius: var(--r-sm) !important;
}

/* Download button in sidebar */
section[data-testid="stSidebar"] .stDownloadButton > button {
    background: var(--bg3) !important;
    color: var(--text1) !important;
    border: 1px solid var(--border1) !important;
    border-radius: var(--r-sm) !important;
    box-shadow: none !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    padding: 9px 12px !important;
    transform: none !important;
}
section[data-testid="stSidebar"] .stDownloadButton > button:hover {
    background: var(--acid-glow) !important;
    border-color: var(--acid-border) !important;
    color: var(--acid) !important;
}

/* ═══════════════════════════════════════════════
   MAIN AREA — HEADER
═══════════════════════════════════════════════ */
.main-hero {
    position: relative;
    padding: 36px 40px 32px;
    border-radius: var(--r-xl);
    margin-bottom: 28px;
    overflow: hidden;
    background: var(--bg1);
    border: 1px solid var(--border1);
}
/* Ambient glow behind hero */
.main-hero::before {
    content: '';
    position: absolute;
    top: -60px; left: -40px;
    width: 340px; height: 260px;
    background: radial-gradient(ellipse, rgba(200,255,87,0.12) 0%, transparent 70%);
    pointer-events: none;
}
.main-hero::after {
    content: '';
    position: absolute;
    bottom: -40px; right: -40px;
    width: 280px; height: 220px;
    background: radial-gradient(ellipse, rgba(0,229,255,0.1) 0%, transparent 70%);
    pointer-events: none;
}
.hero-inner {
    position: relative;
    z-index: 2;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    flex-wrap: wrap;
}
.hero-left {}
.hero-eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--acid);
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.hero-eyebrow::before {
    content: '';
    width: 24px;
    height: 2px;
    background: var(--acid);
    display: inline-block;
}
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: 46px;
    font-weight: 800;
    line-height: 1;
    letter-spacing: -1.5px;
    color: var(--text0);
    margin-bottom: 14px;
}
.hero-title span {
    background: linear-gradient(120deg, var(--acid) 0%, var(--cyan) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.hero-badges {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}
.hero-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    font-weight: 600;
    padding: 5px 13px;
    border-radius: 50px;
    letter-spacing: 0.5px;
}
.badge-gold {
    background: rgba(255,193,7,0.12);
    border: 1px solid rgba(255,193,7,0.35);
    color: #ffc107;
}
.badge-cyan {
    background: var(--cyan-glow);
    border: 1px solid rgba(0,229,255,0.25);
    color: var(--cyan);
}
.badge-acid {
    background: var(--acid-glow);
    border: 1px solid var(--acid-border);
    color: var(--acid);
}

/* Status widget */
.hero-status {
    background: var(--bg2);
    border: 1px solid var(--border1);
    border-radius: var(--r-lg);
    padding: 20px 26px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    min-width: 160px;
    font-family: 'JetBrains Mono', monospace;
}
.status-indicator {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 13px;
    font-weight: 600;
}
.status-dot-pro {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}
.status-online    { background: var(--acid); box-shadow: 0 0 14px rgba(200,255,87,0.7); animation: pDot 2s infinite; }
.status-connecting{ background: #ffaa00;      box-shadow: 0 0 14px rgba(255,170,0,0.7);  animation: pDot 0.9s infinite; }
.status-offline   { background: #ff4646;      box-shadow: 0 0 14px rgba(255,70,70,0.6); }
@keyframes pDot {
    0%,100% { transform:scale(1); opacity:1; }
    50%     { transform:scale(1.35); opacity:0.6; }
}
.status-text-online    { color: var(--acid); }
.status-text-connecting{ color: #ffaa00; }
.status-text-offline   { color: #ff4646; }
.status-uptime {
    font-size: 10px;
    color: var(--text2);
    font-weight: 500;
    letter-spacing: 0.3px;
}

/* ═══════════════════════════════════════════════
   STATS ROW
═══════════════════════════════════════════════ */
.stats-grid-pro {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 14px;
    margin-bottom: 24px;
}
.stat-card-pro {
    background: var(--bg1);
    border: 1px solid var(--border0);
    border-radius: var(--r-md);
    padding: 20px 18px;
    position: relative;
    overflow: hidden;
    cursor: default;
    transition: all 0.25s ease;
}
.stat-card-pro::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--acid), var(--cyan));
    opacity: 0;
    transition: opacity 0.25s;
}
.stat-card-pro:hover {
    background: var(--bg2);
    border-color: var(--border2);
    transform: translateY(-3px);
    box-shadow: 0 14px 40px rgba(0,0,0,0.3);
}
.stat-card-pro:hover::after { opacity: 1; }

.stat-icon-pro {
    font-size: 26px;
    display: block;
    margin-bottom: 12px;
    filter: drop-shadow(0 0 10px rgba(200,255,87,0.3));
}
.stat-label-pro {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--text2);
    display: block;
    margin-bottom: 6px;
}
.stat-value-pro {
    font-family: 'Syne', sans-serif;
    font-size: 36px;
    font-weight: 800;
    color: var(--text0);
    display: block;
    line-height: 1;
    letter-spacing: -1px;
}
.stat-sublabel-pro {
    font-family: 'Manrope', sans-serif;
    font-size: 11px;
    color: var(--text2);
    display: block;
    margin-top: 6px;
}

/* ═══════════════════════════════════════════════
   CHAT CONTAINER
═══════════════════════════════════════════════ */
.chat-container-pro {
    background: var(--bg1);
    border: 1px solid var(--border0);
    border-radius: var(--r-lg);
    padding: 24px;
    min-height: 460px;
    max-height: 560px;
    overflow-y: auto;
    margin-bottom: 18px;
    position: relative;
}

/* Empty state */
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 360px;
    gap: 16px;
    text-align: center;
}
.empty-icon {
    font-size: 56px;
    animation: floatEmoji 3.5s ease-in-out infinite;
    filter: drop-shadow(0 0 18px rgba(200,255,87,0.4));
}
@keyframes floatEmoji {
    0%,100% { transform: translateY(0); }
    50%      { transform: translateY(-12px); }
}
.empty-title {
    font-family: 'Syne', sans-serif;
    font-size: 22px;
    font-weight: 800;
    color: var(--text0);
    letter-spacing: -0.3px;
}
.empty-sub {
    font-family: 'Manrope', sans-serif;
    font-size: 14px;
    color: var(--text2);
    max-width: 360px;
    line-height: 1.7;
}
.empty-chips {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: center;
    margin-top: 6px;
}
.chip {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    padding: 6px 14px;
    border-radius: 50px;
    background: var(--bg3);
    border: 1px solid var(--border1);
    color: var(--text1);
}

/* ═══════════════════════════════════════════════
   MESSAGES
═══════════════════════════════════════════════ */
.message-wrapper-pro {
    margin-bottom: 20px;
    animation: msgIn 0.25s ease-out;
}
@keyframes msgIn {
    from { opacity:0; transform:translateY(6px); }
    to   { opacity:1; transform:translateY(0); }
}
.message-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}
.message-avatar {
    width: 26px;
    height: 26px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 13px;
    flex-shrink: 0;
}
.avatar-user      { background: rgba(200,255,87,0.12); border: 1px solid rgba(200,255,87,0.22); }
.avatar-assistant { background: rgba(0,229,255,0.10);  border: 1px solid rgba(0,229,255,0.20); }

.msg-role {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 500;
    color: var(--text2);
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
.msg-time {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: var(--text2);
    margin-left: auto;
}

.message-user-pro {
    color: var(--text0);
    word-wrap: break-word;
    line-height: 1.65;
    font-size: 14px;
}
.message-user-pro .msg-body {
    background: rgba(200,255,87,0.05);
    border: 1px solid rgba(200,255,87,0.14);
    border-left: 3px solid var(--acid);
    border-radius: 0 10px 10px 10px;
    padding: 13px 16px;
}

.message-assistant-pro {
    color: var(--text0);
    word-wrap: break-word;
    line-height: 1.7;
    font-size: 14px;
}
.message-assistant-pro .msg-body {
    background: var(--bg3);
    border: 1px solid var(--border0);
    border-left: 3px solid var(--cyan);
    border-radius: 0 10px 10px 10px;
    padding: 14px 18px;
}
.message-timestamp-pro {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: var(--text2);
    display: block;
    margin-top: 8px;
    padding-left: 34px;
}

/* ═══════════════════════════════════════════════
   INPUT AREA
═══════════════════════════════════════════════ */
.input-container-pro {
    background: var(--bg1);
    border: 1px solid var(--border1);
    border-radius: var(--r-lg);
    padding: 18px 22px;
    transition: border-color 0.2s;
}
.input-container-pro:focus-within {
    border-color: rgba(200,255,87,0.4);
    box-shadow: 0 0 0 3px rgba(200,255,87,0.06);
}

.stTextInput > div > div > input {
    background: var(--bg2) !important;
    border: 1px solid var(--border1) !important;
    color: var(--text0) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 14px !important;
    border-radius: var(--r-sm) !important;
    padding: 14px 18px !important;
    transition: all 0.2s ease !important;
    caret-color: var(--acid) !important;
}
.stTextInput > div > div > input:focus {
    border-color: rgba(200,255,87,0.45) !important;
    box-shadow: 0 0 0 3px rgba(200,255,87,0.08) !important;
    background: var(--bg0) !important;
}
.stTextInput > div > div > input::placeholder { color: var(--text2) !important; }
.stTextInput > label { display: none !important; }

/* ═══════════════════════════════════════════════
   MAIN BUTTONS (SEND / CLEAR)
═══════════════════════════════════════════════ */
.stButton > button {
    background: var(--acid) !important;
    color: #05080f !important;
    border: none !important;
    border-radius: var(--r-sm) !important;
    padding: 14px 22px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 800 !important;
    font-size: 13px !important;
    letter-spacing: 0.5px !important;
    box-shadow: 0 6px 22px rgba(200,255,87,0.35) !important;
    transition: all 0.2s ease !important;
    text-transform: uppercase !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 32px rgba(200,255,87,0.55) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
}

/* ═══════════════════════════════════════════════
   SHORTCUTS BAR
═══════════════════════════════════════════════ */
.shortcuts-bar {
    text-align: center;
    margin-top: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 18px;
    flex-wrap: wrap;
}
.shortcut {
    display: flex;
    align-items: center;
    gap: 5px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: var(--text2);
}
kbd {
    background: var(--bg3);
    border: 1px solid var(--border1);
    border-radius: 5px;
    padding: 2px 7px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: var(--text1);
}

/* ═══════════════════════════════════════════════
   SCROLLBAR
═══════════════════════════════════════════════ */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border1); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--acid); }

/* ═══════════════════════════════════════════════
   RESPONSIVE
═══════════════════════════════════════════════ */
@media (max-width: 900px) {
    .stats-grid-pro { grid-template-columns: repeat(2,1fr); }
    .hero-title { font-size: 32px; }
    .hero-inner { flex-direction: column; }
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# DATABASE MANAGER
# ============================================================

class ConversationDB:
    def __init__(self, db_path: str = "mcp_conversations.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY, title TEXT,
            created_at TEXT, updated_at TEXT,
            total_messages INTEGER, total_tools_used INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT,
            role TEXT, content TEXT, timestamp TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id))''')
        conn.commit(); conn.close()

    def create_session(self, session_id: str, title: str = "New Conversation"):
        conn = sqlite3.connect(self.db_path)
        now = datetime.now().isoformat()
        conn.execute('''INSERT OR REPLACE INTO sessions
            (session_id,title,created_at,updated_at,total_messages,total_tools_used)
            VALUES(?,?,?,?,0,0)''', (session_id, title, now, now))
        conn.commit(); conn.close()

    def save_message(self, session_id: str, role: str, content: str, timestamp: str):
        conn = sqlite3.connect(self.db_path)
        conn.execute('INSERT INTO messages(session_id,role,content,timestamp) VALUES(?,?,?,?)',
                     (session_id, role, content, timestamp))
        conn.execute('UPDATE sessions SET updated_at=?, total_messages=total_messages+1 WHERE session_id=?',
                     (datetime.now().isoformat(), session_id))
        conn.commit(); conn.close()

    def load_session(self, session_id: str) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT role,content,timestamp FROM messages WHERE session_id=? ORDER BY id ASC', (session_id,))
        msgs = [{'role': r[0], 'content': r[1], 'timestamp': r[2]} for r in c.fetchall()]
        conn.close()
        return msgs

    def get_all_sessions(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''SELECT session_id,title,created_at,updated_at,total_messages,total_tools_used
            FROM sessions ORDER BY updated_at DESC''')
        sessions = [{'session_id':r[0],'title':r[1],'created_at':r[2],
                     'updated_at':r[3],'total_messages':r[4],'total_tools_used':r[5]}
                    for r in c.fetchall()]
        conn.close()
        return sessions


# ============================================================
# MCP CONNECTION MANAGER
# ============================================================

class UltimateMCPManager:
    def __init__(self):
        self.mcp_client = None
        self.agent = None
        self.loop = None
        self.thread = None
        self.connected = False
        self.connecting = False
        self.stats = {
            'messages_sent': 0, 'tools_called': 0, 'resources_accessed': 0,
            'uptime_start': datetime.now(), 'avg_response_time': 0.0,
            'successful_operations': 0, 'failed_operations': 0
        }
        self.db = ConversationDB()

    def start(self):
        if self.thread is None or not self.thread.is_alive():
            self.connecting = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            for _ in range(150):
                if self.connected: break
                time.sleep(0.1)

    def _run_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect())

    async def _connect(self):
        try:
            async with MCPAppClient() as mcp_client:
                self.mcp_client = mcp_client
                self.agent = TerminalAgent(mcp_client, debug_mode=AGENT_DEBUG_MODE)
                self.connected = True; self.connecting = False
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            self.connected = False; self.connecting = False
            print(f"Connection error: {e}")

    def get_tools(self) -> List[Dict[str, Any]]:
        if not self.connected or not self.mcp_client: return []
        return [{'name': t.name, 'description': t.description or f'Tool: {t.name}',
                 'schema': t.inputSchema} for t in self.mcp_client._tools]

    def get_resources(self) -> List[Dict[str, Any]]:
        if not self.connected or not self.mcp_client: return []
        return [{'uri': str(r.uri),
                 'name': r.name or str(r.uri).split('/')[-1] or str(r.uri),
                 'description': r.description or f'Resource: {r.uri}'}
                for r in self.mcp_client._resources]

    def get_prompts(self) -> List[Dict[str, Any]]:
        if not self.connected or not self.mcp_client: return []
        return [{'name': p.name, 'description': p.description or f'Prompt: {p.name}'}
                for p in self.mcp_client._prompts]

    def process_message(self, user_input: str, session_id: str) -> Dict[str, Any]:
        if not self.connected or self.agent is None:
            return {'success': False, 'response': '❌ Connection lost. Please reconnect.',
                    'timestamp': datetime.now().isoformat(), 'execution_time': 0.0}
        self.stats['messages_sent'] += 1
        start_time = time.time()
        result_container = {}

        async def _process():
            try:
                response = await self.agent.answer(user_input)
                elapsed = time.time() - start_time
                n = self.stats['messages_sent']
                self.stats['avg_response_time'] = (self.stats['avg_response_time']*(n-1) + elapsed) / n
                self.stats['successful_operations'] += 1
                result_container['result'] = {'success': True, 'response': response,
                    'timestamp': datetime.now().isoformat(), 'execution_time': elapsed}
            except Exception as e:
                import traceback
                self.stats['failed_operations'] += 1
                result_container['result'] = {'success': False,
                    'response': f"❌ **Error:**\n```python\n{str(e)}\n{traceback.format_exc()}\n```",
                    'timestamp': datetime.now().isoformat(), 'execution_time': time.time()-start_time}

        future = asyncio.run_coroutine_threadsafe(_process(), self.loop)
        try:
            future.result(timeout=300)
        except Exception as e:
            return {'success': False, 'response': f'❌ Timeout: {str(e)}',
                    'timestamp': datetime.now().isoformat(), 'execution_time': time.time()-start_time}

        result = result_container.get('result', {
            'success': False, 'response': '❌ Processing failed',
            'timestamp': datetime.now().isoformat(), 'execution_time': time.time()-start_time})
        ts = result['timestamp']
        self.db.save_message(session_id, 'user', user_input, ts)
        self.db.save_message(session_id, 'assistant', result['response'], ts)
        return result

    def get_uptime(self) -> str:
        if not self.connected: return "Offline"
        total = int((datetime.now() - self.stats['uptime_start']).total_seconds())
        h, rem = divmod(total, 3600); m, s = divmod(rem, 60)
        return f"{h}h {m}m" if h > 0 else (f"{m}m {s}s" if m > 0 else f"{s}s")


# ============================================================
# TOOL CATEGORY HELPERS
# ============================================================

TOOL_CATEGORIES = {
    'terminal':    ['run_command','interactive_command','shell'],
    'filesystem':  ['read_file','write_file','list_directory','search_files','replace_in_file','create_directory','delete_file'],
    'git':         ['git_status','git_diff','git_commit','git_push','git_pull','git_log'],
    'process':     ['list_processes','kill_process','monitor_process'],
    'network':     ['check_port','ping','curl','wget'],
    'docker':      ['docker_ps','docker_exec','docker_logs','docker_compose'],
    'environment': ['get_env','set_env','system_info','platform_info'],
    'monitoring':  ['system_metrics','disk_usage','memory_usage','cpu_usage'],
    'logs':        ['tail_file','grep_logs','analyze_logs'],
}

CAT_ICONS = {
    'terminal':'⚡','filesystem':'📁','git':'🌿','process':'⚙️',
    'network':'🌐','docker':'🐋','environment':'🔬','monitoring':'📊',
    'logs':'📋','other':'🔧'
}

def get_tool_category(name: str) -> str:
    for cat, names in TOOL_CATEGORIES.items():
        if name in names: return cat
    return 'other'


# ============================================================
# RENDERING
# ============================================================

def render_message_pro(message: Dict[str, Any]):
    content = html.escape(message["content"])
    ts = message.get('timestamp', datetime.now().isoformat())
    try:    time_str = datetime.fromisoformat(ts).strftime('%I:%M %p')
    except: time_str = "Now"

    if message["role"] == "user":
        st.markdown(f"""
        <div class="message-wrapper-pro">
            <div class="message-user-pro">
                <div class="message-header">
                    <div class="message-avatar avatar-user">👤</div>
                    <span class="msg-role">You</span>
                    <span class="msg-time">{time_str}</span>
                </div>
                <div class="msg-body">{content}</div>
            </div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="message-wrapper-pro">
            <div class="message-assistant-pro">
                <div class="message-header">
                    <div class="message-avatar avatar-assistant">🤖</div>
                    <span class="msg-role">Assistant</span>
                    <span class="msg-time">{time_str}</span>
                </div>
                <div class="msg-body">{content}</div>
            </div>
        </div>""", unsafe_allow_html=True)


def render_sidebar_pro(manager: UltimateMCPManager):
    with st.sidebar:

        # ── BRAND ──
        st.markdown("""
        <div class="sb-header">
            <div class="sb-logo-row">
                <div class="sb-logo-mark">⚡</div>
                <div class="sb-logo-text">
                    <div class="name">Terminal MCP</div>
                    <div class="tag">v7.0 · Ultimate</div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

        # ── STATUS ──
        if manager.connected:
            st.markdown(f"""
            <div class="sb-status-wrap">
                <div class="sb-status-pill online">
                    <span class="dot"></span>
                    <div class="pill-info">
                        <div class="pill-label">Connected</div>
                        <div class="pill-sub">Uptime: {manager.get_uptime()}</div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
        elif manager.connecting:
            st.markdown("""
            <div class="sb-status-wrap">
                <div class="sb-status-pill connecting">
                    <span class="dot"></span>
                    <div class="pill-info">
                        <div class="pill-label">Connecting…</div>
                        <div class="pill-sub">Establishing MCP link</div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="sb-status-wrap">
                <div class="sb-status-pill offline">
                    <span class="dot"></span>
                    <div class="pill-info">
                        <div class="pill-label">Offline</div>
                        <div class="pill-sub">Server unreachable</div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

        # ── SESSIONS ──
        st.markdown('<div class="sb-section-label">Sessions</div>', unsafe_allow_html=True)
        with st.container():
            st.markdown('<div class="sb-pad">', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("＋ New", use_container_width=True, key="btn_new"):
                    nid = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
                    manager.db.create_session(nid)
                    st.session_state.current_session = nid
                    st.session_state.messages = []
                    st.rerun()
            with c2:
                if st.button("📂 Load", use_container_width=True, key="btn_load"):
                    st.session_state.show_sessions = not st.session_state.get('show_sessions', False)
            st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get('show_sessions', False):
            sessions = manager.db.get_all_sessions()
            if sessions:
                for s in sessions[:6]:
                    title = s['title'][:22] + '…' if len(s['title']) > 22 else s['title']
                    is_active = s['session_id'] == st.session_state.get('current_session', '')
                    pfx = '✅' if is_active else '📝'
                    st.markdown('<div class="sb-pad">', unsafe_allow_html=True)
                    if st.button(f"{pfx} {title}", key=f"sess_{s['session_id']}", use_container_width=True):
                        st.session_state.current_session = s['session_id']
                        st.session_state.messages = manager.db.load_session(s['session_id'])
                        st.session_state.show_sessions = False
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="padding:4px 20px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:var(--text2);">No sessions yet</div>', unsafe_allow_html=True)

        # ── TOOLS ──
        tools = manager.get_tools()
        tools_by_cat: Dict[str, List] = {}
        for t in tools:
            cat = get_tool_category(t['name'])
            tools_by_cat.setdefault(cat, []).append(t)

        with st.expander(f"⚡ Tools  ·  {len(tools)}", expanded=False):
            if tools:
                for cat in sorted(tools_by_cat.keys()):
                    icon = CAT_ICONS.get(cat, '🔧')
                    st.markdown(f'<div class="sb-cat">{icon} {cat}</div>', unsafe_allow_html=True)
                    for t in tools_by_cat[cat]:
                        desc = (t['description'] or '')[:72]
                        st.markdown(f"""
                        <div class="sb-card">
                            <div class="sb-card-top">
                                <span class="sb-card-icon">{icon}</span>
                                <span class="sb-card-name">{t['name']}</span>
                                <span class="sb-card-badge badge-t">{cat}</span>
                            </div>
                            <div class="sb-card-desc">{desc}</div>
                        </div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div style="padding:8px 16px;font-family:Fira Code,monospace;font-size:11px;color:var(--text2);">No tools available</div>', unsafe_allow_html=True)

        # ── RESOURCES ──
        resources = manager.get_resources()
        with st.expander(f"📁 Resources  ·  {len(resources)}", expanded=False):
            if resources:
                for r in resources:
                    cat = r['uri'].split('://')[0] if '://' in r['uri'] else 'other'
                    icon = CAT_ICONS.get(cat, '📄')
                    desc = (r['description'] or '')[:72]
                    st.markdown(f"""
                    <div class="sb-card">
                        <div class="sb-card-top">
                            <span class="sb-card-icon">{icon}</span>
                            <span class="sb-card-name">{r['name']}</span>
                            <span class="sb-card-badge badge-r">{cat}</span>
                        </div>
                        <div class="sb-card-desc">{desc}</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div style="padding:8px 16px;font-family:Fira Code,monospace;font-size:11px;color:var(--text2);">No resources available</div>', unsafe_allow_html=True)

        # ── PROMPTS ──
        prompts = manager.get_prompts()
        with st.expander(f"💬 Prompts  ·  {len(prompts)}", expanded=False):
            if prompts:
                for p in prompts:
                    desc = (p['description'] or '')[:72]
                    st.markdown(f"""
                    <div class="sb-card">
                        <div class="sb-card-top">
                            <span class="sb-card-icon">💬</span>
                            <span class="sb-card-name">{p['name']}</span>
                            <span class="sb-card-badge badge-p">prompt</span>
                        </div>
                        <div class="sb-card-desc">{desc}</div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div style="padding:8px 16px;font-family:Fira Code,monospace;font-size:11px;color:var(--text2);">No prompts available</div>', unsafe_allow_html=True)

        # ── PERFORMANCE STATS ──
        st.markdown('<div class="sb-section-label">Performance</div>', unsafe_allow_html=True)
        total_ops = manager.stats['successful_operations'] + manager.stats['failed_operations']
        sr = int((manager.stats['successful_operations'] / max(1, total_ops)) * 100)
        st.markdown(f"""
        <div class="sb-stats">
            <div class="sb-stat">
                <div class="sb-stat-val">{manager.stats['messages_sent']}</div>
                <div class="sb-stat-label">Messages</div>
            </div>
            <div class="sb-stat">
                <div class="sb-stat-val">{manager.stats['avg_response_time']:.1f}s</div>
                <div class="sb-stat-label">Avg resp.</div>
            </div>
            <div class="sb-stat">
                <div class="sb-stat-val">{sr}%</div>
                <div class="sb-stat-label">Success</div>
            </div>
            <div class="sb-stat">
                <div class="sb-stat-val">{len(tools)}</div>
                <div class="sb-stat-label">Tools</div>
            </div>
        </div>""", unsafe_allow_html=True)

        # ── ACTIONS ──
        st.markdown('<div class="sb-section-label">Actions</div>', unsafe_allow_html=True)
        with st.container():
            st.markdown('<div class="sb-pad">', unsafe_allow_html=True)
            a1, a2 = st.columns(2)
            with a1:
                if st.button("🔄 Refresh", use_container_width=True, key="btn_refresh"):
                    st.rerun()
            with a2:
                if st.session_state.get('messages'):
                    st.download_button(
                        "📥 Export",
                        data=json.dumps(st.session_state.messages, indent=2),
                        file_name=f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True,
                        key="btn_export"
                    )
            st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# MAIN
# ============================================================

def main():
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'mcp_manager' not in st.session_state:
        st.session_state.mcp_manager = UltimateMCPManager()
        st.session_state.mcp_manager.start()
    if 'current_session' not in st.session_state:
        sid = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        st.session_state.current_session = sid
        st.session_state.mcp_manager.db.create_session(sid)
    if 'show_sessions' not in st.session_state:
        st.session_state.show_sessions = False

    manager = st.session_state.mcp_manager

    render_sidebar_pro(manager)

    tools = manager.get_tools()
    resources = manager.get_resources()

    # ── HERO HEADER ──
    if manager.connected:
        status_html = f'''
        <div class="status-indicator">
            <span class="status-dot-pro status-online"></span>
            <span class="status-text-online">ONLINE</span>
        </div>
        <span class="status-uptime">⏱ {manager.get_uptime()} uptime</span>'''
    elif manager.connecting:
        status_html = '''
        <div class="status-indicator">
            <span class="status-dot-pro status-connecting"></span>
            <span class="status-text-connecting">CONNECTING</span>
        </div>'''
    else:
        status_html = '''
        <div class="status-indicator">
            <span class="status-dot-pro status-offline"></span>
            <span class="status-text-offline">OFFLINE</span>
        </div>'''

    st.markdown(f"""
    <div class="main-hero">
        <div class="hero-inner">
            <div class="hero-left">
                <div class="hero-title">Terminal <span>MCP</span> Ultimate</div>
            </div>
            <div class="hero-status">
                {status_html}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── STATS ──
    total_ops = manager.stats['successful_operations'] + manager.stats['failed_operations']
    success_rate = (manager.stats['successful_operations'] / max(1, total_ops)) * 100

    st.markdown(f"""
    <div class="stats-grid-pro">
        <div class="stat-card-pro">
            <span class="stat-icon-pro">💬</span>
            <span class="stat-label-pro">Messages</span>
            <span class="stat-value-pro">{len(st.session_state.messages)}</span>
            <span class="stat-sublabel-pro">This session</span>
        </div>
        <div class="stat-card-pro">
            <span class="stat-icon-pro">🔧</span>
            <span class="stat-label-pro">Tools</span>
            <span class="stat-value-pro">{len(tools)}</span>
            <span class="stat-sublabel-pro">Available</span>
        </div>
        <div class="stat-card-pro">
            <span class="stat-icon-pro">📁</span>
            <span class="stat-label-pro">Resources</span>
            <span class="stat-value-pro">{len(resources)}</span>
            <span class="stat-sublabel-pro">Accessible</span>
        </div>
        <div class="stat-card-pro">
            <span class="stat-icon-pro">⚡</span>
            <span class="stat-label-pro">Response</span>
            <span class="stat-value-pro">{manager.stats['avg_response_time']:.1f}s</span>
            <span class="stat-sublabel-pro">Average time</span>
        </div>
        <div class="stat-card-pro">
            <span class="stat-icon-pro">✅</span>
            <span class="stat-label-pro">Success</span>
            <span class="stat-value-pro">{success_rate:.0f}%</span>
            <span class="stat-sublabel-pro">Success rate</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── CHAT ──
    st.markdown('<div class="chat-container-pro">', unsafe_allow_html=True)

    if not st.session_state.messages:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">⚡</div>
            <div class="empty-title">Terminal Ready</div>
            <div class="empty-sub">AI-powered MCP terminal connected. Type any command or question to begin.</div>
            <div class="empty-chips">
                <span class="chip">ls -la</span>
                <span class="chip">git status</span>
                <span class="chip">docker ps</span>
                <span class="chip">system info</span>
                <span class="chip">disk usage</span>
            </div>
        </div>""", unsafe_allow_html=True)
    else:
        for msg in st.session_state.messages:
            render_message_pro(msg)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── INPUT ──
    st.markdown('<div class="input-container-pro">', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([7, 1.5, 1.5])
    with c1:
        user_input = st.text_input(
            "cmd", placeholder="Type a command or ask anything…",
            label_visibility="collapsed", key="user_input"
        )
    with c2:
        send_button = st.button("⚡ Send", use_container_width=True, type="primary", key="btn_send")
    with c3:
        clear_button = st.button("🗑 Clear", use_container_width=True, key="btn_clear")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="shortcuts-bar">
        <span class="shortcut"><kbd>Enter</kbd> Send</span>
        <span class="shortcut"><kbd>Ctrl+K</kbd> Clear</span>
        <span class="shortcut"><kbd>↑↓</kbd> History</span>
        <span class="shortcut" style="color:var(--text2);font-family:'Fira Code',monospace;font-size:10px;">
            session <span style="color:rgba(200,255,87,0.6);">{st.session_state.current_session}</span>
        </span>
    </div>""", unsafe_allow_html=True)

    if clear_button:
        st.session_state.messages = []
        st.rerun()

    if send_button and user_input:
        ts = datetime.now().isoformat()
        st.session_state.messages.append({"role": "user", "content": user_input, "timestamp": ts})
        with st.spinner("Processing…"):
            result = manager.process_message(user_input, st.session_state.current_session)
        st.session_state.messages.append({
            "role": "assistant",
            "content": result['response'],
            "timestamp": result.get('timestamp', ts)
        })
        st.rerun()


if __name__ == "__main__":
    main()


