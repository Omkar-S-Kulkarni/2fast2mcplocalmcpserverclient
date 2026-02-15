"""
Terminal MCP Client - Streamlit Frontend
Maintains persistent MCP connection exactly like run.py
"""

import streamlit as st
import asyncio
import threading
from client import MCPAppClient
from agent_verbose import TerminalAgent

# Page config
st.set_page_config(
    page_title="Terminal MCP Client",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
    
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%);
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .terminal-container {
        background: rgba(10, 14, 39, 0.95);
        border: 2px solid #00ff88;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 0 40px rgba(0, 255, 136, 0.3);
        font-family: 'JetBrains Mono', monospace;
        margin: 20px 0;
        max-height: 600px;
        overflow-y: auto;
    }
    
    .terminal-header {
        background: linear-gradient(90deg, #00ff88 0%, #00ccff 100%);
        padding: 15px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0, 255, 136, 0.4);
    }
    
    .terminal-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 28px;
        font-weight: 700;
        color: #0a0e27;
        margin: 0;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }
    
    .user-message {
        background: linear-gradient(135deg, #00ff88 0%, #00ccff 100%);
        color: #0a0e27;
        padding: 12px 18px;
        border-radius: 8px;
        margin: 10px 0;
        font-family: 'JetBrains Mono', monospace;
        font-weight: 600;
        box-shadow: 0 2px 10px rgba(0, 255, 136, 0.3);
    }
    
    .assistant-message {
        background: rgba(255, 255, 255, 0.05);
        border-left: 4px solid #00ff88;
        color: #e0e0e0;
        padding: 12px 18px;
        border-radius: 8px;
        margin: 10px 0;
        font-family: 'JetBrains Mono', monospace;
        line-height: 1.6;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    
    .stTextInput > div > div > input {
        background: rgba(0, 0, 0, 0.4) !important;
        border: 2px solid #00ff88 !important;
        color: #e0e0e0 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 16px !important;
        border-radius: 8px !important;
        padding: 12px !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #00ccff !important;
        box-shadow: 0 0 15px rgba(0, 255, 136, 0.5) !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #00ff88 0%, #00ccff 100%) !important;
        color: #0a0e27 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 30px !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        box-shadow: 0 4px 15px rgba(0, 255, 136, 0.4) !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(0, 255, 136, 0.6) !important;
    }
    
    .stats-container {
        display: flex;
        gap: 15px;
        margin: 15px 0;
    }
    
    .stat-box {
        background: rgba(0, 255, 136, 0.1);
        border: 1px solid #00ff88;
        border-radius: 8px;
        padding: 10px 15px;
        flex: 1;
        text-align: center;
    }
    
    .stat-label {
        color: #00ff88;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .stat-value {
        color: #e0e0e0;
        font-size: 20px;
        font-weight: 700;
        margin-top: 5px;
    }
    
    ::-webkit-scrollbar {
        width: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(0, 0, 0, 0.2);
    }
    
    ::-webkit-scrollbar-thumb {
        background: #00ff88;
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #00ccff;
    }
</style>
""", unsafe_allow_html=True)

# Background thread manager for async MCP client
class MCPConnectionManager:
    def __init__(self):
        self.mcp_client = None
        self.agent = None
        self.loop = None
        self.thread = None
        self.connected = False
        self.lock = threading.Lock()
        
    def start(self):
        """Start MCP client in background thread"""
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            # Wait for connection
            import time
            for _ in range(50):  # Wait up to 5 seconds
                if self.connected:
                    break
                time.sleep(0.1)
    
    def _run_loop(self):
        """Run async event loop in background thread - EXACTLY like run.py"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._connect_and_serve())
    
    async def _connect_and_serve(self):
        """Connect to MCP and keep connection alive - EXACTLY like run.py"""
        async with MCPAppClient() as mcp_client:
            self.mcp_client = mcp_client
            self.agent = TerminalAgent(mcp_client)
            self.connected = True
            
            # Keep connection alive forever (like run.py does)
            while True:
                await asyncio.sleep(0.1)
    
    def process_message(self, user_input):
        """Process message using persistent agent"""
        if not self.connected or self.agent is None:
            return {
                'success': False,
                'response': '❌ Not connected. Please refresh the page.',
                'tools': 0,
                'resources': 0,
                'prompts': 0
            }
        
        result_container = {}
        
        async def _process():
            try:
                response = await self.agent.answer(user_input)
                result_container['result'] = {
                    'success': True,
                    'response': response,
                    'tools': len(self.mcp_client._tools),
                    'resources': len(self.mcp_client._resources),
                    'prompts': len(self.mcp_client._prompts)
                }
            except Exception as e:
                import traceback
                result_container['result'] = {
                    'success': False,
                    'response': f"❌ Error: {str(e)}\n\n{traceback.format_exc()}",
                    'tools': 0,
                    'resources': 0,
                    'prompts': 0
                }
        
        # Schedule coroutine in the persistent loop
        future = asyncio.run_coroutine_threadsafe(_process(), self.loop)
        future.result(timeout=300)  # 5 minute timeout
        
        return result_container.get('result', {
            'success': False,
            'response': '❌ Processing failed',
            'tools': 0,
            'resources': 0,
            'prompts': 0
        })

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'mcp_manager' not in st.session_state:
    st.session_state.mcp_manager = MCPConnectionManager()
    st.session_state.mcp_manager.start()

# Main UI
def main():
    # Header
    st.markdown("""
    <div class="terminal-header">
        <h1 class="terminal-title">🖥️ Terminal MCP Client</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Stats display
    manager = st.session_state.mcp_manager
    status_emoji = "🟢" if manager.connected else "🔴"
    status_text = "Connected" if manager.connected else "Connecting..."
    
    tools = len(manager.mcp_client._tools) if manager.connected and manager.mcp_client else 0
    resources = len(manager.mcp_client._resources) if manager.connected and manager.mcp_client else 0
    
    st.markdown(f"""
    <div class="stats-container">
        <div class="stat-box">
            <div class="stat-label">Status</div>
            <div class="stat-value">{status_emoji} {status_text}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Messages</div>
            <div class="stat-value">{len(st.session_state.messages)}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Tools</div>
            <div class="stat-value">{tools}</div>
        </div>
        <div class="stat-box">
            <div class="stat-label">Resources</div>
            <div class="stat-value">{resources}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Chat container
    st.markdown('<div class="terminal-container">', unsafe_allow_html=True)
    
    # Display chat messages
    if not st.session_state.messages:
        st.markdown('<div class="assistant-message">🤖 Terminal MCP Client ready. Type a command to begin.</div>', unsafe_allow_html=True)
    
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f'<div class="user-message">🖥️ > {message["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="assistant-message">🤖 {message["content"]}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Input area
    col1, col2, col3 = st.columns([5, 1, 1])
    
    with col1:
        user_input = st.text_input(
            "Command",
            placeholder="Type your question here...",
            label_visibility="collapsed",
            key="user_input"
        )
    
    with col2:
        send_button = st.button("▶ Send", use_container_width=True)
    
    with col3:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    
    # Process input
    if send_button and user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Show thinking indicator
        with st.spinner("🤖 Thinking..."):
            # Process message using persistent connection
            result = manager.process_message(user_input)
        
        # Add assistant message
        st.session_state.messages.append({
            "role": "assistant", 
            "content": result['response']
        })
        
        # Rerun to update UI
        st.rerun()

if __name__ == "__main__":
    main()