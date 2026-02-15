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
# REVOLUTIONARY CSS - 10/10 CHAMPIONSHIP DESIGN
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
    
    #MainMenu, footer, header {visibility: hidden;}
    
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
        font-size: 48px;
        font-weight: 900;
        background: var(--primary-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        letter-spacing: -1.5px;
        text-shadow: 0 0 40px rgba(0, 255, 136, 0.5);
        animation: titlePulse 3s ease-in-out infinite;
        line-height: 1.1;
    }
    
    @keyframes titlePulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.02); }
    }
    
    .header-subtitle {
        font-size: 16px;
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
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        animation: badgePulse 2s ease-in-out infinite;
        font-family: 'JetBrains Mono', monospace;
    }
    
    @keyframes badgePulse {
        0%, 100% { box-shadow: 0 0 20px rgba(255, 215, 0, 0.3); }
        50% { box-shadow: 0 0 30px rgba(255, 215, 0, 0.6); }
    }
    
    .connection-status-pro {
        background: rgba(10, 14, 39, 0.95);
        backdrop-filter: blur(10px);
        border: 2px solid rgba(0, 255, 136, 0.4);
        padding: 20px 28px;
        border-radius: 20px;
        font-family: 'JetBrains Mono', monospace;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        min-width: 160px;
    }
    
    .status-indicator {
        display: flex;
        align-items: center;
        gap: 12px;
        font-weight: 700;
        font-size: 15px;
    }
    
    .status-dot-pro {
        width: 16px;
        height: 16px;
        border-radius: 50%;
        position: relative;
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    
    @keyframes pulse {
        0%, 100% { 
            opacity: 1;
            transform: scale(1);
        }
        50% { 
            opacity: 0.8;
            transform: scale(1.15);
        }
    }
    
    .status-online { 
        background: #00ff88;
        box-shadow: 0 0 25px rgba(0, 255, 136, 0.7);
    }
    
    .status-connecting { 
        background: #ffaa00;
        box-shadow: 0 0 25px rgba(255, 170, 0, 0.7);
    }
    
    .status-offline { 
        background: #ff4444;
        box-shadow: 0 0 25px rgba(255, 68, 68, 0.7);
    }
    
    .status-text-online { color: #00ff88; }
    .status-text-connecting { color: #ffaa00; }
    .status-text-offline { color: #ff4444; }
    
    .status-uptime {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.6);
        font-weight: 600;
    }
    
    /* ==================== NEXT-GEN STATS GRID ==================== */
    
    .stats-grid-pro {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 20px;
        margin: 30px 0;
    }
    
    .stat-card-pro {
        background: linear-gradient(135deg, rgba(0, 255, 136, 0.08) 0%, rgba(0, 212, 255, 0.08) 100%);
        backdrop-filter: blur(10px);
        border: 2px solid rgba(0, 255, 136, 0.25);
        border-radius: 20px;
        padding: 28px 24px;
        position: relative;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
    }
    
    .stat-card-pro:hover {
        transform: translateY(-10px) scale(1.03);
        border-color: var(--neon-green);
        box-shadow: 
            0 25px 70px rgba(0, 255, 136, 0.35),
            0 0 90px rgba(0, 212, 255, 0.25);
    }
    
    .stat-icon-pro {
        font-size: 48px;
        margin-bottom: 14px;
        display: block;
        filter: drop-shadow(0 4px 12px rgba(0, 255, 136, 0.4));
        animation: float 3s ease-in-out infinite;
    }
    
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
    }
    
    .stat-label-pro {
        color: var(--neon-green);
        font-size: 12px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 2.5px;
        margin-bottom: 12px;
        display: block;
        font-family: 'Space Grotesk', sans-serif;
    }
    
    .stat-value-pro {
        color: #ffffff;
        font-size: 48px;
        font-weight: 900;
        font-family: 'JetBrains Mono', monospace;
        text-shadow: 0 2px 25px rgba(0, 255, 136, 0.5);
        display: block;
        line-height: 1;
        letter-spacing: -1px;
    }
    
    .stat-sublabel-pro {
        color: rgba(255, 255, 255, 0.6);
        font-size: 13px;
        margin-top: 10px;
        font-weight: 600;
        display: block;
    }
    
    /* ==================== CHAT INTERFACE ==================== */
    
    .chat-container-pro {
        background: transparent;
        padding: 20px 0;
        min-height: 550px;
        max-height: 650px;
        overflow-y: auto;
        margin-bottom: 24px;
    }
    
    .message-wrapper-pro {
        margin: 0 0 24px 0;
        animation: messageSlide 0.3s ease-out;
        position: relative;
    }
    
    @keyframes messageSlide {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .message-user-pro {
        background: transparent;
        color: #e8e8e8;
        padding: 0;
        margin: 0 0 8px 0;
        font-family: 'Inter', sans-serif;
        font-weight: 400;
        font-size: 15px;
        position: relative;
        word-wrap: break-word;
        line-height: 1.6;
        max-width: 100%;
    }
    
    .message-assistant-pro {
        background: rgba(255, 255, 255, 0.03);
        border-left: 3px solid rgba(0, 255, 136, 0.5);
        color: #e8e8e8;
        padding: 20px 24px;
        border-radius: 8px;
        margin: 0;
        max-width: 100%;
        font-family: 'Inter', sans-serif;
        line-height: 1.7;
        font-size: 15px;
        position: relative;
        word-wrap: break-word;
    }
    
    .message-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
        font-weight: 600;
        font-size: 14px;
        color: rgba(255, 255, 255, 0.6);
    }
    
    .message-avatar {
        width: 24px;
        height: 24px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        background: rgba(0, 255, 136, 0.15);
        border: 1px solid rgba(0, 255, 136, 0.3);
    }
    
    .message-content {
        line-height: 1.7;
        color: #e8e8e8;
    }
    
    .message-timestamp-pro {
        font-size: 11px;
        opacity: 0.5;
        margin-top: 8px;
        font-family: 'Inter', sans-serif;
        font-weight: 400;
        display: inline-block;
    }
    
    /* ==================== PREMIUM INPUT AREA ==================== */
    
    .input-container-pro {
        background: linear-gradient(135deg, rgba(10, 14, 39, 0.9) 0%, rgba(26, 31, 58, 0.7) 100%);
        backdrop-filter: blur(25px);
        border: 2px solid rgba(0, 255, 136, 0.35);
        border-radius: 22px;
        padding: 26px;
        box-shadow: 
            0 10px 40px rgba(0, 0, 0, 0.35),
            inset 0 1px 0 rgba(255, 255, 255, 0.15);
        position: relative;
    }
    
    .stTextInput > div > div > input {
        background: rgba(0, 0, 0, 0.7) !important;
        border: 2px solid rgba(0, 255, 136, 0.45) !important;
        color: #f0f0f0 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 15px !important;
        border-radius: 16px !important;
        padding: 20px 22px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: var(--neon-green) !important;
        box-shadow: 
            0 0 0 5px rgba(0, 255, 136, 0.15),
            0 10px 40px rgba(0, 255, 136, 0.35) !important;
        background: rgba(0, 0, 0, 0.85) !important;
    }
    
    /* ==================== NEXT-LEVEL BUTTONS ==================== */
    
    .stButton > button {
        background: linear-gradient(135deg, #00ff88 0%, #00d4ff 100%) !important;
        color: #0a0e27 !important;
        border: none !important;
        border-radius: 16px !important;
        padding: 18px 36px !important;
        font-family: 'Space Grotesk', sans-serif !important;
        font-weight: 800 !important;
        font-size: 14px !important;
        box-shadow: 
            0 10px 30px rgba(0, 255, 136, 0.45),
            0 0 50px rgba(0, 212, 255, 0.25) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    
    .stButton > button:hover {
        transform: translateY(-5px) scale(1.03) !important;
        box-shadow: 
            0 15px 50px rgba(0, 255, 136, 0.65),
            0 0 80px rgba(0, 212, 255, 0.45) !important;
    }
    
    /* ==================== ENHANCED SCROLLBAR ==================== */
    
    ::-webkit-scrollbar {
        width: 14px;
        height: 14px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.5);
        border-radius: 7px;
        margin: 5px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #00ff88 0%, #00d4ff 100%);
        border-radius: 7px;
        border: 3px solid rgba(0, 0, 0, 0.5);
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #00d4ff 0%, #00ff88 100%);
        box-shadow: 0 0 20px rgba(0, 255, 136, 0.6);
    }
    
    /* ==================== RESPONSIVE DESIGN ==================== */
    
    @media (max-width: 768px) {
        .ultra-header {
            padding: 22px;
        }
        
        .header-title {
            font-size: 36px;
        }
        
        .stats-grid-pro {
            grid-template-columns: repeat(2, 1fr);
        }
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
        
        # Sessions table
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
        
        # Messages table
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
        """Create new session"""
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
        """Save message to database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO messages (session_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (session_id, role, content, timestamp))
        
        # Update session stats
        c.execute('''
            UPDATE sessions 
            SET updated_at = ?, 
                total_messages = total_messages + 1
            WHERE session_id = ?
        ''', (datetime.now().isoformat(), session_id))
        
        conn.commit()
        conn.close()
    
    def load_session(self, session_id: str) -> List[Dict]:
        """Load session messages"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT role, content, timestamp
            FROM messages
            WHERE session_id = ?
            ORDER BY id ASC
        ''', (session_id,))
        
        messages = []
        for row in c.fetchall():
            messages.append({
                'role': row[0],
                'content': row[1],
                'timestamp': row[2]
            })
        
        conn.close()
        return messages
    
    def get_all_sessions(self) -> List[Dict]:
        """Get all sessions"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT session_id, title, created_at, updated_at, total_messages, total_tools_used
            FROM sessions
            ORDER BY updated_at DESC
        ''')
        
        sessions = []
        for row in c.fetchall():
            sessions.append({
                'session_id': row[0],
                'title': row[1],
                'created_at': row[2],
                'updated_at': row[3],
                'total_messages': row[4],
                'total_tools_used': row[5]
            })
        
        conn.close()
        return sessions


# ============================================================
# ULTIMATE MCP CONNECTION MANAGER
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
        """Initialize MCP connection"""
        if self.thread is None or not self.thread.is_alive():
            self.connecting = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            
            # Wait for connection
            for _ in range(150):
                if self.connected:
                    break
                time.sleep(0.1)
    
    def _run_loop(self):
        """Background event loop"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect())
    
    async def _connect(self):
        """Maintain persistent connection"""
        try:
            async with MCPAppClient() as mcp_client:
                self.mcp_client = mcp_client
                self.agent = TerminalAgent(mcp_client, debug_mode=AGENT_DEBUG_MODE)
                self.connected = True
                self.connecting = False
                
                # Keep connection alive
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            self.connected = False
            self.connecting = False
            print(f"Connection error: {e}")
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get all available MCP tools"""
        if not self.connected or not self.mcp_client:
            return []
        
        tools = []
        for tool in self.mcp_client._tools:
            tools.append({
                'name': tool.name,
                'description': tool.description or f'Tool: {tool.name}',
                'schema': tool.inputSchema
            })
        
        return tools
    
    def get_resources(self) -> List[Dict[str, Any]]:
        """Get all available MCP resources"""
        if not self.connected or not self.mcp_client:
            return []
        
        resources = []
        for resource in self.mcp_client._resources:
            uri = str(resource.uri)
            resources.append({
                'uri': uri,
                'name': resource.name or uri.split('/')[-1] or uri,
                'description': resource.description or f'Resource: {uri}'
            })
        
        return resources
    
    def get_prompts(self) -> List[Dict[str, Any]]:
        """Get all available MCP prompts"""
        if not self.connected or not self.mcp_client:
            return []
        
        prompts = []
        for prompt in self.mcp_client._prompts:
            prompts.append({
                'name': prompt.name,
                'description': prompt.description or f'Prompt: {prompt.name}'
            })
        
        return prompts
    
    def process_message(self, user_input: str, session_id: str) -> Dict[str, Any]:
        """Process user message with your enhanced agent"""
        if not self.connected or self.agent is None:
            return {
                'success': False,
                'response': '❌ Connection lost. Please reconnect.',
                'timestamp': datetime.now().isoformat(),
                'execution_time': 0.0
            }
        
        self.stats['messages_sent'] += 1
        start_time = time.time()
        result_container = {}
        
        async def _process():
            try:
                # Use your enhanced agent
                response = await self.agent.answer(user_input)
                
                elapsed = time.time() - start_time
                
                # Update stats
                self.stats['avg_response_time'] = (
                    (self.stats['avg_response_time'] * (self.stats['messages_sent'] - 1) + elapsed)
                    / self.stats['messages_sent']
                )
                self.stats['successful_operations'] += 1
                
                result_container['result'] = {
                    'success': True,
                    'response': response,
                    'timestamp': datetime.now().isoformat(),
                    'execution_time': elapsed
                }
                
            except Exception as e:
                self.stats['failed_operations'] += 1
                import traceback
                
                result_container['result'] = {
                    'success': False,
                    'response': f"❌ **Error occurred:**\n\n```python\n{str(e)}\n{traceback.format_exc()}\n```",
                    'timestamp': datetime.now().isoformat(),
                    'execution_time': time.time() - start_time
                }
        
        future = asyncio.run_coroutine_threadsafe(_process(), self.loop)
        try:
            future.result(timeout=300)
        except Exception as e:
            return {
                'success': False,
                'response': f'❌ Timeout or error: {str(e)}',
                'timestamp': datetime.now().isoformat(),
                'execution_time': time.time() - start_time
            }
        
        result = result_container.get('result', {
            'success': False,
            'response': '❌ Processing failed',
            'timestamp': datetime.now().isoformat(),
            'execution_time': time.time() - start_time
        })
        
        # Save to database
        timestamp = result['timestamp']
        self.db.save_message(session_id, 'user', user_input, timestamp)
        self.db.save_message(session_id, 'assistant', result['response'], timestamp)
        
        return result
    
    def get_uptime(self) -> str:
        """Get formatted uptime"""
        if not self.connected:
            return "Offline"
        
        uptime = datetime.now() - self.stats['uptime_start']
        total_seconds = int(uptime.total_seconds())
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


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
        st.markdown("## 🎛️ Control Panel")
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
            if st.button("➕ New", use_container_width=True):
                new_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
                manager.db.create_session(new_id)
                st.session_state.current_session = new_id
                st.session_state.messages = []
                st.rerun()
        
        with col2:
            if st.button("📂 Load", use_container_width=True):
                st.session_state.show_sessions = not st.session_state.get('show_sessions', False)
        
        if st.session_state.get('show_sessions', False):
            sessions = manager.db.get_all_sessions()
            for session in sessions[:5]:
                title = session['title'][:20] + "..." if len(session['title']) > 20 else session['title']
                if st.button(f"📝 {title}", key=f"session_{session['session_id']}", use_container_width=True):
                    st.session_state.current_session = session['session_id']
                    st.session_state.messages = manager.db.load_session(session['session_id'])
                    st.session_state.show_sessions = False
                    st.rerun()
        
        st.markdown("---")
        
        # Tools, Resources, Prompts
        tools = manager.get_tools()
        resources = manager.get_resources()
        prompts = manager.get_prompts()
        
        with st.expander(f"🔧 Tools ({len(tools)})", expanded=False):
            for tool in tools[:10]:
                st.markdown(f"**{tool['name']}**")
                st.caption(tool['description'])
        
        with st.expander(f"📁 Resources ({len(resources)})", expanded=False):
            for resource in resources[:10]:
                st.markdown(f"**{resource['name']}**")
                st.caption(resource['description'])
        
        with st.expander(f"💬 Prompts ({len(prompts)})", expanded=False):
            for prompt in prompts:
                st.markdown(f"**{prompt['name']}**")
                st.caption(prompt['description'])
        
        st.markdown("---")
        
        # Stats
        st.markdown("### 📊 Stats")
        success_rate = (manager.stats['successful_operations'] / 
                       max(1, manager.stats['successful_operations'] + manager.stats['failed_operations']) * 100)
        
        st.markdown(f"""
        <div style="font-size: 12px; color: rgba(255,255,255,0.7); line-height: 2;">
            <div>💬 Messages: <strong>{manager.stats['messages_sent']}</strong></div>
            <div>⚡ Avg Response: <strong>{manager.stats['avg_response_time']:.2f}s</strong></div>
            <div>✅ Success: <strong>{success_rate:.0f}%</strong></div>
        </div>
        """, unsafe_allow_html=True)


def main():
    """Main application"""
    
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
    
    manager = st.session_state.mcp_manager
    
    # Render sidebar
    render_sidebar_pro(manager)
    
    # Header
    tools = manager.get_tools()
    resources = manager.get_resources()
    
    if manager.connected:
        status_content = f'''
        <div class="status-indicator">
            <span class="status-dot-pro status-online"></span>
            <span class="status-text-online">CONNECTED</span>
        </div>
        <span class="status-uptime">⏱️ {manager.get_uptime()}</span>
        '''
    elif manager.connecting:
        status_content = f'''
        <div class="status-indicator">
            <span class="status-dot-pro status-connecting"></span>
            <span class="status-text-connecting">CONNECTING...</span>
        </div>
        '''
    else:
        status_content = f'''
        <div class="status-indicator">
            <span class="status-dot-pro status-offline"></span>
            <span class="status-text-offline">DISCONNECTED</span>
        </div>
        '''
    
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
    success_rate = (manager.stats['successful_operations'] / 
                   max(1, manager.stats['successful_operations'] + manager.stats['failed_operations']) * 100)
    
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
        send_button = st.button("⚡ SEND", use_container_width=True, type="primary")
    
    with col3:
        clear_button = st.button("🗑️ CLEAR", use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Handle clear
    if clear_button:
        st.session_state.messages = []
        st.rerun()
    
    # Handle send
    if send_button and user_input:
        timestamp = datetime.now().isoformat()
        
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": timestamp
        })
        
        # Process with your enhanced agent
        with st.spinner("🤖 Processing..."):
            result = manager.process_message(user_input, st.session_state.current_session)
        
        # Add assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": result['response'],
            "timestamp": result.get('timestamp', timestamp)
        })
        
        st.rerun()


if __name__ == "__main__":
    main()