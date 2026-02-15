"""
TERMINAL MCP CLIENT ULTIMATE - CHAMPIONSHIP EDITION
🏆 International Hackathon Winner
Complete Feature Set: Streaming + Persistence + Advanced UI + All Power Features
INTEGRATED WITH ENHANCED PHASE 1-7 AGENT
"""

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

# Import your existing modules
from client import MCPAppClient
from agent import TerminalAgent  # Using your enhanced agent
from config import AGENT_DEBUG_MODE

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Terminal MCP Ultimate",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS - FIXED SIDEBAR TOGGLE + CHAMPIONSHIP DESIGN
# ============================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&family=Space+Grotesk:wght@300;400;500;600;700;800;900&family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* ==================== GLOBAL FOUNDATION ==================== */

    :root {
        --primary-gradient: linear-gradient(135deg, #00ff88 0%, #00d4ff 50%, #0099ff 100%);
        --secondary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --dark-gradient: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1429 100%);
        --glass-bg: rgba(255, 255, 255, 0.05);
        --glass-border: rgba(255, 255, 255, 0.1);
        --neon-green: #00ff88;
        --neon-blue: #00d4ff;
        --neon-purple: #a78bfa;
        --neon-orange: #ff6b35;
        --dark-bg: #0a0e27;
        --card-bg: rgba(26, 31, 58, 0.6);
    }

    * {
        box-sizing: border-box;
    }

    .stApp {
        background: var(--dark-gradient);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #e0e0e0;
    }

    #MainMenu, footer, header { visibility: hidden; }

    /* ==================== SIDEBAR TOGGLE - ALWAYS VISIBLE ==================== */

    /* The >>> button when sidebar is COLLAPSED - must always show */
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
        background: linear-gradient(135deg, #00ff88 0%, #00d4ff 100%) !important;
        color: #0a0e27 !important;
        border: none !important;
        border-radius: 0 14px 14px 0 !important;
        width: 28px !important;
        min-width: 28px !important;
        height: 72px !important;
        padding: 0 !important;
        cursor: pointer !important;
        box-shadow: 4px 0 24px rgba(0, 255, 136, 0.6) !important;
        transition: width 0.2s ease, box-shadow 0.2s ease !important;
        align-items: center !important;
        justify-content: center !important;
        flex-direction: column !important;
        gap: 4px !important;
    }

    [data-testid="collapsedControl"]:hover {
        width: 38px !important;
        box-shadow: 6px 0 36px rgba(0, 255, 136, 0.9) !important;
    }

    /* Override any SVG inside the collapsed button */
    [data-testid="collapsedControl"] svg {
        color: #0a0e27 !important;
        fill: #0a0e27 !important;
        width: 14px !important;
        height: 14px !important;
    }

    /* The <<< button inside the sidebar when it IS expanded */
    [data-testid="baseButton-header"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        background: rgba(0, 255, 136, 0.1) !important;
        border: 1px solid rgba(0, 255, 136, 0.35) !important;
        color: #00ff88 !important;
        border-radius: 8px !important;
        padding: 6px 10px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
    }

    [data-testid="baseButton-header"]:hover {
        background: rgba(0, 255, 136, 0.25) !important;
        border-color: #00ff88 !important;
        box-shadow: 0 0 16px rgba(0, 255, 136, 0.3) !important;
    }

    [data-testid="baseButton-header"] svg {
        color: #00ff88 !important;
        fill: #00ff88 !important;
    }

    /* Sidebar background */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0e27 0%, #1a1f3a 100%) !important;
        border-right: 2px solid rgba(0, 255, 136, 0.25) !important;
    }

    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 16px !important;
    }

    /* ==================== ULTRA PREMIUM HEADER ==================== */

    .ultra-header {
        background: linear-gradient(135deg, rgba(0, 255, 136, 0.15) 0%, rgba(0, 212, 255, 0.15) 100%);
        backdrop-filter: blur(20px);
        border: 2px solid rgba(0, 255, 136, 0.3);
        border-radius: 24px;
        padding: 30px 40px;
        margin-bottom: 30px;
        box-shadow:
            0 20px 60px rgba(0, 255, 136, 0.3),
            0 0 100px rgba(0, 212, 255, 0.2),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
        position: relative;
        overflow: hidden;
        animation: headerGlow 3s ease-in-out infinite;
    }

    @keyframes headerGlow {
        0%, 100% { box-shadow: 0 20px 60px rgba(0, 255, 136, 0.3), 0 0 100px rgba(0, 212, 255, 0.2); }
        50% { box-shadow: 0 20px 60px rgba(0, 255, 136, 0.5), 0 0 120px rgba(0, 212, 255, 0.4); }
    }

    .ultra-header::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: conic-gradient(
            from 0deg,
            transparent 0deg,
            rgba(0, 255, 136, 0.1) 30deg,
            transparent 90deg,
            transparent 180deg,
            rgba(0, 212, 255, 0.1) 210deg,
            transparent 270deg,
            transparent 360deg
        );
        animation: rotate 20s linear infinite;
    }

    @keyframes rotate {
        100% { transform: rotate(360deg); }
    }

    .ultra-header::after {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
        animation: shine 5s infinite;
    }

    @keyframes shine {
        0% { left: -100%; }
        50%, 100% { left: 200%; }
    }

    .header-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: relative;
        z-index: 2;
        gap: 20px;
        flex-wrap: wrap;
    }

    .header-left {
        flex: 1;
        min-width: 300px;
    }

    .header-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 42px;
        font-weight: 900;
        background: var(--primary-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        letter-spacing: -1.5px;
        animation: titlePulse 3s ease-in-out infinite;
        line-height: 1.1;
    }

    @keyframes titlePulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.01); }
    }

    .header-subtitle {
        font-size: 14px;
        color: rgba(0, 255, 136, 0.9);
        font-weight: 700;
        margin-top: 8px;
        letter-spacing: 3px;
        text-transform: uppercase;
        font-family: 'JetBrains Mono', monospace;
    }

    .header-badges {
        display: flex;
        gap: 10px;
        margin-top: 12px;
        flex-wrap: wrap;
    }

    .header-badge {
        background: linear-gradient(135deg, rgba(255, 215, 0, 0.2), rgba(255, 140, 0, 0.2));
        border: 2px solid rgba(255, 215, 0, 0.6);
        color: #ffd700;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-family: 'JetBrains Mono', monospace;
    }

    .connection-status-pro {
        background: rgba(10, 14, 39, 0.95);
        border: 2px solid rgba(0, 255, 136, 0.4);
        padding: 20px 24px;
        border-radius: 20px;
        font-family: 'JetBrains Mono', monospace;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        min-width: 150px;
    }

    .status-indicator {
        display: flex;
        align-items: center;
        gap: 12px;
        font-weight: 700;
        font-size: 14px;
    }

    .status-dot-pro {
        width: 14px;
        height: 14px;
        border-radius: 50%;
        flex-shrink: 0;
    }

    .status-online {
        background: #00ff88;
        box-shadow: 0 0 20px rgba(0, 255, 136, 0.8);
        animation: pulseDot 2s ease-in-out infinite;
    }

    .status-connecting {
        background: #ffaa00;
        box-shadow: 0 0 20px rgba(255, 170, 0, 0.8);
        animation: pulseDot 1s ease-in-out infinite;
    }

    .status-offline {
        background: #ff4444;
        box-shadow: 0 0 20px rgba(255, 68, 68, 0.8);
    }

    @keyframes pulseDot {
        0%, 100% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.3); opacity: 0.7; }
    }

    .status-text-online { color: #00ff88; }
    .status-text-connecting { color: #ffaa00; }
    .status-text-offline { color: #ff4444; }

    .status-uptime {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.6);
        font-weight: 600;
    }

    /* ==================== STATS GRID ==================== */

    .stats-grid-pro {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 16px;
        margin: 24px 0;
    }

    .stat-card-pro {
        background: linear-gradient(135deg, rgba(0, 255, 136, 0.08) 0%, rgba(0, 212, 255, 0.08) 100%);
        border: 2px solid rgba(0, 255, 136, 0.2);
        border-radius: 18px;
        padding: 24px 20px;
        position: relative;
        overflow: hidden;
        transition: all 0.3s ease;
        cursor: pointer;
    }

    .stat-card-pro:hover {
        transform: translateY(-6px);
        border-color: var(--neon-green);
        box-shadow: 0 20px 50px rgba(0, 255, 136, 0.3);
    }

    .stat-icon-pro {
        font-size: 36px;
        margin-bottom: 12px;
        display: block;
        animation: floatIcon 3s ease-in-out infinite;
    }

    @keyframes floatIcon {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-6px); }
    }

    .stat-label-pro {
        color: var(--neon-green);
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 8px;
        display: block;
        font-family: 'Space Grotesk', sans-serif;
    }

    .stat-value-pro {
        color: #ffffff;
        font-size: 40px;
        font-weight: 900;
        font-family: 'JetBrains Mono', monospace;
        display: block;
        line-height: 1;
        letter-spacing: -1px;
    }

    .stat-sublabel-pro {
        color: rgba(255, 255, 255, 0.5);
        font-size: 12px;
        margin-top: 8px;
        display: block;
    }

    /* ==================== CHAT INTERFACE ==================== */

    .chat-container-pro {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 24px;
        min-height: 500px;
        max-height: 600px;
        overflow-y: auto;
        margin-bottom: 20px;
    }

    .message-wrapper-pro {
        margin: 0 0 24px 0;
        animation: messageSlide 0.3s ease-out;
    }

    @keyframes messageSlide {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .message-user-pro {
        color: #e8e8e8;
        margin: 0 0 8px 0;
        font-family: 'Inter', sans-serif;
        font-size: 15px;
        word-wrap: break-word;
        line-height: 1.6;
    }

    .message-assistant-pro {
        background: rgba(255, 255, 255, 0.04);
        border-left: 3px solid rgba(0, 255, 136, 0.6);
        color: #e8e8e8;
        padding: 18px 22px;
        border-radius: 0 12px 12px 12px;
        font-family: 'Inter', sans-serif;
        line-height: 1.7;
        font-size: 14px;
        word-wrap: break-word;
    }

    .message-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
        font-weight: 600;
        font-size: 13px;
        color: rgba(255, 255, 255, 0.55);
    }

    .message-avatar {
        width: 26px;
        height: 26px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        background: rgba(0, 255, 136, 0.15);
        border: 1px solid rgba(0, 255, 136, 0.3);
        flex-shrink: 0;
    }

    .message-content {
        line-height: 1.7;
        color: #e8e8e8;
    }

    .message-timestamp-pro {
        font-size: 11px;
        opacity: 0.45;
        margin-top: 8px;
        font-family: 'JetBrains Mono', monospace;
        display: inline-block;
    }

    /* Welcome screen */
    .welcome-screen {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 380px;
        text-align: center;
        gap: 16px;
    }

    .welcome-icon {
        font-size: 72px;
        animation: floatIcon 3s ease-in-out infinite;
        filter: drop-shadow(0 0 20px rgba(0, 255, 136, 0.5));
    }

    .welcome-title {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 26px;
        font-weight: 800;
        background: var(--primary-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .welcome-text {
        color: rgba(255, 255, 255, 0.6);
        font-size: 15px;
        max-width: 420px;
        line-height: 1.7;
    }

    /* ==================== INPUT AREA ==================== */

    .input-container-pro {
        background: linear-gradient(135deg, rgba(10, 14, 39, 0.9) 0%, rgba(26, 31, 58, 0.7) 100%);
        border: 2px solid rgba(0, 255, 136, 0.35);
        border-radius: 20px;
        padding: 20px 24px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }

    .stTextInput > div > div > input {
        background: rgba(0, 0, 0, 0.6) !important;
        border: 2px solid rgba(0, 255, 136, 0.4) !important;
        color: #f0f0f0 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 15px !important;
        border-radius: 14px !important;
        padding: 16px 20px !important;
        transition: all 0.3s ease !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: var(--neon-green) !important;
        box-shadow: 0 0 0 4px rgba(0, 255, 136, 0.12),
                    0 8px 30px rgba(0, 255, 136, 0.2) !important;
        background: rgba(0, 0, 0, 0.8) !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: rgba(255, 255, 255, 0.35) !important;
    }

    .stTextInput > label { display: none !important; }

    /* ==================== MAIN BUTTONS ==================== */

    .stButton > button {
        background: linear-gradient(135deg, #00ff88 0%, #00d4ff 100%) !important;
        color: #0a0e27 !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 16px 28px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 800 !important;
        font-size: 13px !important;
        box-shadow: 0 8px 25px rgba(0, 255, 136, 0.4) !important;
        transition: all 0.25s ease !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 12px 35px rgba(0, 255, 136, 0.6) !important;
    }

    .stButton > button:active {
        transform: translateY(-1px) !important;
    }

    /* ==================== SIDEBAR INTERNALS ==================== */

    section[data-testid="stSidebar"] .stMarkdown h2 {
        color: var(--neon-green) !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 18px !important;
        font-weight: 800 !important;
    }

    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: rgba(255, 255, 255, 0.8) !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 14px !important;
        font-weight: 700 !important;
    }

    /* Sidebar buttons styled differently from main buttons */
    section[data-testid="stSidebar"] .stButton > button {
        background: rgba(0, 255, 136, 0.1) !important;
        color: #00ff88 !important;
        border: 1px solid rgba(0, 255, 136, 0.3) !important;
        box-shadow: none !important;
        font-size: 12px !important;
        padding: 10px 14px !important;
        transform: none !important;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(0, 255, 136, 0.2) !important;
        border-color: var(--neon-green) !important;
        box-shadow: 0 4px 15px rgba(0, 255, 136, 0.2) !important;
        transform: none !important;
    }

    /* Sidebar download button */
    section[data-testid="stSidebar"] .stDownloadButton > button {
        background: rgba(0, 255, 136, 0.1) !important;
        color: #00ff88 !important;
        border: 1px solid rgba(0, 255, 136, 0.3) !important;
        box-shadow: none !important;
        font-size: 12px !important;
        padding: 10px 14px !important;
    }

    section[data-testid="stSidebar"] .stDownloadButton > button:hover {
        background: rgba(0, 255, 136, 0.2) !important;
    }

    /* Sidebar expanders */
    .streamlit-expanderHeader {
        background: rgba(0, 255, 136, 0.08) !important;
        border: 1px solid rgba(0, 255, 136, 0.2) !important;
        border-radius: 10px !important;
        color: var(--neon-green) !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 700 !important;
        font-size: 13px !important;
        padding: 12px 16px !important;
    }

    .streamlit-expanderHeader:hover {
        background: rgba(0, 255, 136, 0.15) !important;
        border-color: var(--neon-green) !important;
    }

    /* Success/Warning/Error alerts in sidebar */
    section[data-testid="stSidebar"] .stSuccess {
        background: rgba(0, 255, 136, 0.1) !important;
        border: 1px solid rgba(0, 255, 136, 0.3) !important;
        color: #00ff88 !important;
        border-radius: 10px !important;
    }

    section[data-testid="stSidebar"] .stWarning {
        background: rgba(255, 170, 0, 0.1) !important;
        border: 1px solid rgba(255, 170, 0, 0.3) !important;
        color: #ffaa00 !important;
        border-radius: 10px !important;
    }

    section[data-testid="stSidebar"] .stError {
        background: rgba(255, 68, 68, 0.1) !important;
        border: 1px solid rgba(255, 68, 68, 0.3) !important;
        color: #ff4444 !important;
        border-radius: 10px !important;
    }

    /* ==================== SCROLLBAR ==================== */

    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.4); border-radius: 4px; }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #00ff88, #00d4ff);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover { background: #00ff88; }

    /* ==================== RESPONSIVE ==================== */

    @media (max-width: 768px) {
        .header-title { font-size: 28px; }
        .stats-grid-pro { grid-template-columns: repeat(2, 1fr); }
        .header-content { flex-direction: column; }
    }
</style>
""", unsafe_allow_html=True)


# ============================================================
# DATABASE MANAGER FOR PERSISTENCE
# ============================================================

class ConversationDB:
    """Enterprise-grade conversation persistence"""

    def __init__(self, db_path: str = "mcp_conversations.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize database with schema"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT,
                updated_at TEXT,
                total_messages INTEGER,
                total_tools_used INTEGER
            )
        ''')

        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (session_id)
            )
        ''')

        conn.commit()
        conn.close()

    def create_session(self, session_id: str, title: str = "New Conversation"):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute('''
            INSERT OR REPLACE INTO sessions
            (session_id, title, created_at, updated_at, total_messages, total_tools_used)
            VALUES (?, ?, ?, ?, 0, 0)
        ''', (session_id, title, now, now))
        conn.commit()
        conn.close()

    def save_message(self, session_id: str, role: str, content: str, timestamp: str):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO messages (session_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (session_id, role, content, timestamp))
        c.execute('''
            UPDATE sessions
            SET updated_at = ?, total_messages = total_messages + 1
            WHERE session_id = ?
        ''', (datetime.now().isoformat(), session_id))
        conn.commit()
        conn.close()

    def load_session(self, session_id: str) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT role, content, timestamp FROM messages
            WHERE session_id = ? ORDER BY id ASC
        ''', (session_id,))
        messages = [{'role': r[0], 'content': r[1], 'timestamp': r[2]} for r in c.fetchall()]
        conn.close()
        return messages

    def get_all_sessions(self) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            SELECT session_id, title, created_at, updated_at, total_messages, total_tools_used
            FROM sessions ORDER BY updated_at DESC
        ''')
        sessions = [{'session_id': r[0], 'title': r[1], 'created_at': r[2],
                     'updated_at': r[3], 'total_messages': r[4], 'total_tools_used': r[5]}
                    for r in c.fetchall()]
        conn.close()
        return sessions


# ============================================================
# MCP CONNECTION MANAGER
# ============================================================

class UltimateMCPManager:
    """Championship-level MCP manager with all Phase 1-7 features"""

    def __init__(self):
        self.mcp_client = None
        self.agent = None
        self.loop = None
        self.thread = None
        self.connected = False
        self.connecting = False

        self.stats = {
            'messages_sent': 0,
            'tools_called': 0,
            'resources_accessed': 0,
            'uptime_start': datetime.now(),
            'avg_response_time': 0.0,
            'successful_operations': 0,
            'failed_operations': 0
        }

        self.db = ConversationDB()

    def start(self):
        if self.thread is None or not self.thread.is_alive():
            self.connecting = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            for _ in range(150):
                if self.connected:
                    break
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
                self.connected = True
                self.connecting = False
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            self.connected = False
            self.connecting = False
            print(f"Connection error: {e}")

    def get_tools(self) -> List[Dict[str, Any]]:
        if not self.connected or not self.mcp_client:
            return []
        return [{'name': t.name, 'description': t.description or f'Tool: {t.name}',
                 'schema': t.inputSchema} for t in self.mcp_client._tools]

    def get_resources(self) -> List[Dict[str, Any]]:
        if not self.connected or not self.mcp_client:
            return []
        resources = []
        for r in self.mcp_client._resources:
            uri = str(r.uri)
            resources.append({'uri': uri, 'name': r.name or uri.split('/')[-1] or uri,
                               'description': r.description or f'Resource: {uri}'})
        return resources

    def get_prompts(self) -> List[Dict[str, Any]]:
        if not self.connected or not self.mcp_client:
            return []
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
                self.stats['avg_response_time'] = (
                    (self.stats['avg_response_time'] * (n - 1) + elapsed) / n
                )
                self.stats['successful_operations'] += 1
                result_container['result'] = {
                    'success': True, 'response': response,
                    'timestamp': datetime.now().isoformat(), 'execution_time': elapsed
                }
            except Exception as e:
                import traceback
                self.stats['failed_operations'] += 1
                result_container['result'] = {
                    'success': False,
                    'response': f"❌ **Error:**\n\n```python\n{str(e)}\n{traceback.format_exc()}\n```",
                    'timestamp': datetime.now().isoformat(),
                    'execution_time': time.time() - start_time
                }

        future = asyncio.run_coroutine_threadsafe(_process(), self.loop)
        try:
            future.result(timeout=300)
        except Exception as e:
            return {'success': False, 'response': f'❌ Timeout: {str(e)}',
                    'timestamp': datetime.now().isoformat(),
                    'execution_time': time.time() - start_time}

        result = result_container.get('result', {
            'success': False, 'response': '❌ Processing failed',
            'timestamp': datetime.now().isoformat(),
            'execution_time': time.time() - start_time
        })

        ts = result['timestamp']
        self.db.save_message(session_id, 'user', user_input, ts)
        self.db.save_message(session_id, 'assistant', result['response'], ts)

        return result

    def get_uptime(self) -> str:
        if not self.connected:
            return "Offline"
        total = int((datetime.now() - self.stats['uptime_start']).total_seconds())
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h > 0:
            return f"{h}h {m}m"
        elif m > 0:
            return f"{m}m {s}s"
        else:
            return f"{s}s"


# ============================================================
# RENDERING FUNCTIONS
# ============================================================

def render_message_pro(message: Dict[str, Any]):
    """Render chat message"""
    timestamp = message.get('timestamp', datetime.now().isoformat())
    try:
        time_str = datetime.fromisoformat(timestamp).strftime('%I:%M %p')
    except:
        time_str = "Now"

    if message["role"] == "user":
        st.markdown(f"""
        <div class="message-wrapper-pro">
            <div class="message-user-pro">
                <div class="message-header">
                    <div class="message-avatar">👤</div>
                    <span>You</span>
                </div>
                <div class="message-content">{message["content"]}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="message-wrapper-pro">
            <div class="message-assistant-pro">
                <div class="message-header">
                    <div class="message-avatar">🤖</div>
                    <span>Assistant</span>
                </div>
                <div class="message-content">{message["content"]}</div>
                <span class="message-timestamp-pro">{time_str}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_sidebar_pro(manager: UltimateMCPManager):
    """Enhanced sidebar with Phase 1-7 features"""

    with st.sidebar:
        st.markdown("## ⚡ Control Panel")
        st.markdown("---")

        # Connection Status
        if manager.connected:
            st.success(f"🟢 **Connected** • ⏱️ {manager.get_uptime()}")
        elif manager.connecting:
            st.warning("🟡 **Connecting...**")
        else:
            st.error("🔴 **Offline**")

        st.markdown("---")

        # Session Management
        st.markdown("### 💾 Sessions")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ New", use_container_width=True, key="btn_new_session"):
                new_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
                manager.db.create_session(new_id)
                st.session_state.current_session = new_id
                st.session_state.messages = []
                st.rerun()

        with col2:
            if st.button("📂 Load", use_container_width=True, key="btn_load_toggle"):
                st.session_state.show_sessions = not st.session_state.get('show_sessions', False)

        if st.session_state.get('show_sessions', False):
            sessions = manager.db.get_all_sessions()
            if sessions:
                for session in sessions[:5]:
                    title = session['title'][:20] + "..." if len(session['title']) > 20 else session['title']
                    is_active = session['session_id'] == st.session_state.get('current_session', '')
                    label = f"{'✅' if is_active else '📝'} {title}"
                    if st.button(label, key=f"session_{session['session_id']}", use_container_width=True):
                        st.session_state.current_session = session['session_id']
                        st.session_state.messages = manager.db.load_session(session['session_id'])
                        st.session_state.show_sessions = False
                        st.rerun()
            else:
                st.caption("No saved sessions yet.")

        st.markdown("---")

        # Tools, Resources, Prompts
        tools = manager.get_tools()
        resources = manager.get_resources()
        prompts = manager.get_prompts()

        with st.expander(f"🔧 Tools ({len(tools)})", expanded=False):
            if tools:
                for tool in tools:
                    st.markdown(f"**`{tool['name']}`**")
                    st.caption(tool['description'])
                    st.markdown("")
            else:
                st.caption("No tools available.")

        with st.expander(f"📁 Resources ({len(resources)})", expanded=False):
            if resources:
                for resource in resources:
                    st.markdown(f"**`{resource['name']}`**")
                    st.caption(resource['description'])
                    st.markdown("")
            else:
                st.caption("No resources available.")

        with st.expander(f"💬 Prompts ({len(prompts)})", expanded=False):
            if prompts:
                for prompt in prompts:
                    st.markdown(f"**`{prompt['name']}`**")
                    st.caption(prompt['description'])
                    st.markdown("")
            else:
                st.caption("No prompts available.")

        st.markdown("---")

        # Actions row
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh", use_container_width=True, key="btn_refresh"):
                st.rerun()
        with col2:
            if st.session_state.get('messages'):
                chat_json = json.dumps(st.session_state.messages, indent=2)
                st.download_button(
                    "📥 Export",
                    data=chat_json,
                    file_name=f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True,
                    key="btn_export"
                )

        st.markdown("---")

        # Stats
        st.markdown("### 📊 Stats")
        total_ops = manager.stats['successful_operations'] + manager.stats['failed_operations']
        success_rate = (manager.stats['successful_operations'] / max(1, total_ops)) * 100

        st.markdown(f"""
        <div style="font-size: 13px; color: rgba(255,255,255,0.75);
                    line-height: 2.2; font-family: 'JetBrains Mono', monospace;">
            <div>💬 Messages: <strong style="color:#00ff88;">{manager.stats['messages_sent']}</strong></div>
            <div>⚡ Avg Response: <strong style="color:#00ff88;">{manager.stats['avg_response_time']:.2f}s</strong></div>
            <div>✅ Success Rate: <strong style="color:#00ff88;">{success_rate:.0f}%</strong></div>
        </div>
        """, unsafe_allow_html=True)


# ============================================================
# MAIN APPLICATION
# ============================================================

def main():
    """Main application entry point"""

    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    if 'mcp_manager' not in st.session_state:
        st.session_state.mcp_manager = UltimateMCPManager()
        st.session_state.mcp_manager.start()

    if 'current_session' not in st.session_state:
        session_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        st.session_state.current_session = session_id
        st.session_state.mcp_manager.db.create_session(session_id)

    if 'show_sessions' not in st.session_state:
        st.session_state.show_sessions = False

    manager = st.session_state.mcp_manager

    # Render sidebar FIRST (important for layout)
    render_sidebar_pro(manager)

    # ── MAIN CONTENT AREA ──

    tools = manager.get_tools()
    resources = manager.get_resources()

    # Status content for header
    if manager.connected:
        status_content = f'''
        <div class="status-indicator">
            <span class="status-dot-pro status-online"></span>
            <span class="status-text-online">CONNECTED</span>
        </div>
        <span class="status-uptime">⏱️ {manager.get_uptime()}</span>
        '''
    elif manager.connecting:
        status_content = '''
        <div class="status-indicator">
            <span class="status-dot-pro status-connecting"></span>
            <span class="status-text-connecting">CONNECTING...</span>
        </div>
        '''
    else:
        status_content = '''
        <div class="status-indicator">
            <span class="status-dot-pro status-offline"></span>
            <span class="status-text-offline">DISCONNECTED</span>
        </div>
        '''

    # Header
    st.markdown(f"""
    <div class="ultra-header">
        <div class="header-content">
            <div class="header-left">
                <h1 class="header-title">⚡ Terminal MCP Ultimate</h1>
                <div class="header-subtitle">🏆 Championship Edition • Phases 1-7 Complete</div>
                <div class="header-badges">
                    <span class="header-badge">42+ Tools</span>
                    <span class="header-badge">9 Resources</span>
                    <span class="header-badge">AI-Powered</span>
                </div>
            </div>
            <div class="connection-status-pro">
                {status_content}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Stats Dashboard
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
            <span class="stat-sublabel-pro">Average</span>
        </div>
        <div class="stat-card-pro">
            <span class="stat-icon-pro">✅</span>
            <span class="stat-label-pro">Success</span>
            <span class="stat-value-pro">{success_rate:.0f}%</span>
            <span class="stat-sublabel-pro">Rate</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Chat Container
    st.markdown('<div class="chat-container-pro">', unsafe_allow_html=True)

    if not st.session_state.messages:
        st.markdown("""
        <div class="welcome-screen">
            <div class="welcome-icon">⚡</div>
            <div class="welcome-title">Terminal MCP Ready</div>
            <div class="welcome-text">
                Your AI-powered terminal is connected and ready.<br>
                Type a command below to get started.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for message in st.session_state.messages:
            render_message_pro(message)

    st.markdown('</div>', unsafe_allow_html=True)

    # Input Area
    st.markdown('<div class="input-container-pro">', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([7, 1.5, 1.5])

    with col1:
        user_input = st.text_input(
            "Command",
            placeholder="What would you like me to do?",
            label_visibility="collapsed",
            key="user_input"
        )

    with col2:
        send_button = st.button("⚡ SEND", use_container_width=True, type="primary", key="btn_send")

    with col3:
        clear_button = st.button("🗑️ CLEAR", use_container_width=True, key="btn_clear")

    st.markdown('</div>', unsafe_allow_html=True)

    # Keyboard hint
    st.markdown(f"""
    <div style="text-align:center; color:rgba(255,255,255,0.3); font-size:11px;
                margin-top:14px; font-family:'JetBrains Mono',monospace; letter-spacing:0.5px;">
        Press <kbd style="background:rgba(255,255,255,0.1); border:1px solid rgba(255,255,255,0.2);
        border-radius:4px; padding:2px 7px; font-size:10px;">Enter</kbd> to send &nbsp;•&nbsp;
        Session: <span style="color:rgba(0,255,136,0.6);">{st.session_state.current_session}</span>
    </div>
    """, unsafe_allow_html=True)

    # Handle clear
    if clear_button:
        st.session_state.messages = []
        st.rerun()

    # Handle send
    if send_button and user_input:
        timestamp = datetime.now().isoformat()

        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": timestamp
        })

        with st.spinner("🤖 Processing..."):
            result = manager.process_message(user_input, st.session_state.current_session)

        st.session_state.messages.append({
            "role": "assistant",
            "content": result['response'],
            "timestamp": result.get('timestamp', timestamp)
        })

        st.rerun()


if __name__ == "__main__":
    main()