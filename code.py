# app.py
import asyncio
import json
import sys
import streamlit as st
import ollama
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
import requests
import base64
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import tempfile
import os


# ---- Load and encode logo ----
def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None


# ---- Check if Ollama is running ----
def check_ollama_status():
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False


# ---- Test remote server connection ----
def test_remote_connection(ip_address, username, password):
    """Test SSH connection to remote server"""
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip_address, username=username, password=password, timeout=5)
        ssh.close()
        return True, "Connection successful"
    except ImportError:
        return False, "paramiko library not installed. Run: pip install paramiko"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


# ---- Fetch remote file via SFTP ----
def fetch_remote_file(ip_address, username, password, remote_path):
    """Download file from remote server via SFTP to temp location"""
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip_address, username=username, password=password, timeout=10)
        
        sftp = ssh.open_sftp()
        
        # Create temp file to store downloaded content
        temp_dir = tempfile.gettempdir()
        local_filename = os.path.basename(remote_path)
        local_path = os.path.join(temp_dir, f"remote_{local_filename}")
        
        sftp.get(remote_path, local_path)
        sftp.close()
        ssh.close()
        
        return True, local_path
    except ImportError:
        return False, "paramiko library not installed. Run: pip install paramiko"
    except Exception as e:
        return False, f"File fetch failed: {str(e)}"


# ---- Get latest file from remote directory ----
def get_latest_remote_file(ip_address, username, password, remote_dir):
    """Get the most recently modified file from a remote directory"""
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip_address, username=username, password=password, timeout=10)
        
        sftp = ssh.open_sftp()
        
        # List all files in directory
        files = []
        for entry in sftp.listdir_attr(remote_dir):
            if not entry.filename.startswith('.'):
                files.append((entry.filename, entry.st_mtime))
        
        sftp.close()
        ssh.close()
        
        if not files:
            return False, "No files found in directory"
        
        # Sort by modification time and get latest
        latest_file = sorted(files, key=lambda x: x[1], reverse=True)[0][0]
        latest_path = f"{remote_dir.rstrip('/')}/{latest_file}"
        
        return True, latest_path
    except ImportError:
        return False, "paramiko library not installed. Run: pip install paramiko"
    except Exception as e:
        return False, f"Error listing directory: {str(e)}"


# ---- Tail remote file (get last N lines) ----
def tail_remote_file(ip_address, username, password, remote_path, lines=100):
    """Get last N lines from a remote file via SSH"""
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip_address, username=username, password=password, timeout=10)
        
        # Use tail command on remote server
        stdin, stdout, stderr = ssh.exec_command(f"tail -n {lines} {remote_path}")
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        ssh.close()
        
        if error:
            return False, f"Error: {error}"
        
        # Save to temp file
        temp_dir = tempfile.gettempdir()
        local_filename = f"tail_{os.path.basename(remote_path)}"
        local_path = os.path.join(temp_dir, local_filename)
        
        with open(local_path, 'w', encoding='utf-8') as f:
            f.write(output)
        
        return True, local_path
    except ImportError:
        return False, "paramiko library not installed. Run: pip install paramiko"
    except Exception as e:
        return False, f"Tail failed: {str(e)}"


# ---- Core: ask the LLM, let it call MCP tools, return final text ----
async def ask_with_mcp_tools(question: str, model: str = "qwen3:4b", remote_config=None):
    # 1) Start your MCP server via STDIO (runs server.py with same interpreter)
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["server.py"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 2) Initialize and discover tools from the MCP server
            await session.initialize()
            tools_resp = await session.list_tools()

            # Build Ollama-compatible tool schema list
            # (Prefer tool.inputSchema; fall back if name differs)
            ollama_tools = []
            for tool in tools_resp.tools:
                name = getattr(tool, "name", None) or tool.get("name")
                desc = getattr(tool, "description", None) or tool.get("description") or ""
                schema = (
                    getattr(tool, "inputSchema", None)
                    or getattr(tool, "input_schema", None)
                    or tool.get("inputSchema")
                    or tool.get("input_schema")
                    or {"type": "object", "properties": {}}
                )
                ollama_tools.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": desc,
                        "parameters": schema,
                    }
                })

            # 3) Detect if question mentions file paths and auto-prepare tool call
            import re as regex_module
            # Support both Windows paths and Linux paths for remote servers
            file_path_match = regex_module.search(r'[A-Za-z]:\\[^\s]+\.log|/[^\s]+\.log|[\w_-]+\.log', question)
            
            # If remote connection is enabled and file path detected, fetch the file
            actual_file_path = None
            if file_path_match and remote_config and remote_config.get("enabled") and remote_config.get("connected"):
                remote_path = file_path_match.group(0)
                success, result = fetch_remote_file(
                    remote_config["ip"],
                    remote_config["username"],
                    remote_config["password"],
                    remote_path
                )
                if success:
                    actual_file_path = result  # Local temp path
                    print(f"[DEBUG] Fetched remote file from {remote_path} to {actual_file_path}")
                else:
                    return f"Error fetching remote file: {result}"
            elif file_path_match:
                actual_file_path = file_path_match.group(0)
            
            # Determine which tool to use based on context
            is_apache = any(keyword in question.lower() for keyword in ['apache', 'access', 'web server', 'http'])
            tool_to_use = "analyze_apache_log" if is_apache else "analyze_report_log"
            
            # Enhanced system prompt to force tool usage
            system_prompt = (
                "You are a PSR Report Analysis Assistant with access to specialized tools. "
                "CRITICAL RULES:\n"
                "1. NEVER write Python code or scripts - always use the available tools\n"
                "2. When asked about log files or report details, IMMEDIATELY use the analyze_report_log tool\n"
                "3. Do not explain how to do something - just use the tool and return the results\n"
                "4. Extract file paths from the user's question and pass them to the tool\n"
                "5. If a .log file is mentioned, you MUST use analyze_report_log tool\n"
            )
            
            # If file path detected, make the prompt more explicit
            user_content = question
            if actual_file_path:
                user_content = f"Use the analyze_report_log tool to analyze: {actual_file_path}"
            
            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                tools=ollama_tools,
            )

            # The Python client returns a typed object; access via attributes is supported
            # (README shows response.message.content usage).
            # We'll also be resilient to dict-style access. [4](https://deepwiki.com/ollama/ollama/3-api-reference)[5](https://realpython.com/python-mcp-client/)
            message = response.message if hasattr(response, "message") else response["message"]

            # 4) If the model wants to call a tool, execute it via MCP
            tool_calls = getattr(message, "tool_calls", None) or message.get("tool_calls")
            
            # FALLBACK: If model didn't call tool but file path detected, force tool call
            if not tool_calls and actual_file_path:
                # DEBUG: Log that we're using fallback
                print(f"[DEBUG] Model didn't call tool. Using fallback to call {tool_to_use} with: {actual_file_path}")
                
                # Manually construct tool call with the appropriate tool
                tool_result = await session.call_tool(tool_to_use, {"log_file_path": actual_file_path})
                
                # Extract result
                content = getattr(tool_result, "content", None)
                if content is None:
                    content_str = str(tool_result)
                elif isinstance(content, list) and len(content) > 0:
                    first_item = content[0]
                    if hasattr(first_item, "text"):
                        content_str = first_item.text
                    elif isinstance(first_item, dict) and "text" in first_item:
                        content_str = first_item["text"]
                    else:
                        content_str = str(first_item)
                else:
                    content_str = str(content)
                
                print(f"[DEBUG] MCP Tool Result (first 200 chars): {content_str[:200]}")
                return content_str
            
            if tool_calls:
                # DEBUG: Log that model called tool naturally
                print(f"[DEBUG] Model called tool naturally: {tool_calls}")
                
                # Handle the first tool call (you can loop for many)
                tool_call = tool_calls[0]
                fn = getattr(tool_call, "function", None) or tool_call.get("function")
                tool_name = getattr(fn, "name", None) or fn.get("name")
                arguments = getattr(fn, "arguments", None) or fn.get("arguments") or {}

                # Execute the MCP tool
                tool_result = await session.call_tool(tool_name, arguments)

                # Convert tool result to a string payload for the follow-up call
                # MCP returns content as a list of content items, extract the text
                content = getattr(tool_result, "content", None)
                if content is None:
                    content_str = str(tool_result)
                elif isinstance(content, list) and len(content) > 0:
                    # Extract text from first content item
                    first_item = content[0]
                    if hasattr(first_item, "text"):
                        content_str = first_item.text
                    elif isinstance(first_item, dict) and "text" in first_item:
                        content_str = first_item["text"]
                    else:
                        content_str = str(first_item)
                else:
                    content_str = str(content)

                # 5) Second chat call: send (user, assistant:tool_calls, tool:<result>)
                # Per Ollama tool-calling docs, the "tool" message uses 'tool_name' key. [1](https://docs.ollama.com/capabilities/tool-calling)
                assistant_msg = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {"name": tool_name, "arguments": arguments},
                        }
                    ],
                }

                final_response = ollama.chat(
                    model=model,
                    messages=[
                        {"role": "user", "content": question},
                        assistant_msg,
                        {"role": "tool", "tool_name": tool_name, "content": content_str},
                    ],
                )
                final_message = final_response.message if hasattr(final_response, "message") else final_response["message"]
                return final_message.content if hasattr(final_message, "content") else final_message["content"]

            # 6) Otherwise, the model answered directly
            return message.content if hasattr(message, "content") else message["content"]


def render_apache_analysis(apache_data):
    """Render Apache log analysis with charts and metrics"""
    try:
        data = json.loads(apache_data)
        
        if "error" in data:
            st.error(f"❌ {data['error']}")
            return
        
        # Summary metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Requests", f"{data['summary']['total_requests']:,}")
        with col2:
            st.metric("Avg Response", f"{data['summary']['avg_response_time_ms']:.0f} ms")
        with col3:
            st.metric("P95 Response", f"{data['summary']['p95_response_time_ms']:,} ms")
        with col4:
            error_rate = data['summary']['error_rate_percent']
            st.metric("Error Rate", f"{error_rate:.2f}%", delta=f"{'🔴' if error_rate > 5 else '🟢'}")
        
        st.divider()
        
        # Charts row
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.subheader("📊 Status Code Distribution")
            status_data = data['status_codes']
            fig_status = go.Figure(data=[go.Pie(
                labels=['2xx Success', '4xx Client Error', '5xx Server Error'],
                values=[status_data['success_2xx'], status_data['client_error_4xx'], status_data['server_error_5xx']],
                marker=dict(colors=['#00ff88', '#ffaa00', '#ff4444']),
                hole=0.4
            )])
            fig_status.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e8e8e8', size=12),
                showlegend=True,
                height=300
            )
            st.plotly_chart(fig_status, use_container_width=True)
        
        with chart_col2:
            st.subheader("⏱️ Response Time Distribution")
            rt_dist = data['response_time_dist']
            fig_rt = go.Figure(data=[go.Bar(
                x=list(rt_dist.keys()),
                y=list(rt_dist.values()),
                marker=dict(color='#00d9ff'),
                text=list(rt_dist.values()),
                textposition='auto'
            )])
            fig_rt.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#e8e8e8'),
                xaxis=dict(title='Response Time', gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(title='Count', gridcolor='rgba(255,255,255,0.1)'),
                height=300
            )
            st.plotly_chart(fig_rt, use_container_width=True)
        
        st.divider()
        
        # Tables
        table_col1, table_col2 = st.columns(2)
        
        with table_col1:
            st.subheader("🔝 Top 10 Endpoints")
            import pandas as pd
            endpoints_df = pd.DataFrame(data['top_endpoints'])
            if not endpoints_df.empty:
                endpoints_df.index = range(1, len(endpoints_df) + 1)
                st.dataframe(endpoints_df, use_container_width=True)
        
        with table_col2:
            st.subheader("👥 Top 5 Client IPs")
            ips_df = pd.DataFrame(data['top_ips'])
            if not ips_df.empty:
                ips_df.index = range(1, len(ips_df) + 1)
                st.dataframe(ips_df, use_container_width=True)
        
    except json.JSONDecodeError:
        st.error("Failed to parse Apache log analysis results")
    except Exception as e:
        st.error(f"Error rendering Apache analysis: {str(e)}")


# ---- Streamlit UI ----
st.set_page_config(page_title="MCP ↔ Ollama ↔ Streamlit", page_icon="🧰", layout="centered")

# Load external CSS
def load_css(file_path):
    with open(file_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css(r"C:\Users\abpawar\OneDrive - NiCE Ltd\Desktop\AI_Initiative\styles.css")

# Add logo
logo_path = r"C:\Users\abpawar\OneDrive - NiCE Ltd\Desktop\AI_Initiative\NiceLogo.png"
logo_base64 = get_base64_image(logo_path)

if logo_base64:
    st.markdown(f"""
    <div class="logo-container">
        <img src="data:image/png;base64,{logo_base64}" alt="NiCE Logo">
    </div>
    """, unsafe_allow_html=True)

st.title("🔍 PSR Report AI Tool")
st.markdown("""
<p style='text-align: center; color: #6b7c99; font-size: 14px; margin-top: -10px; margin-bottom: 15px; font-family: "Segoe UI", sans-serif;'>
    Powered by <span style='color: #00d9ff;'>MCP ↔ Ollama ↔ Streamlit</span>
</p>
""", unsafe_allow_html=True)

# Settings panel (solid, non-collapsible)
try:
    _settings_panel = st.container(border=True)
except TypeError:
    _settings_panel = st.container()

with _settings_panel:
    st.markdown("<div class='settings-title'>Settings</div>", unsafe_allow_html=True)

    model = st.selectbox(
        "Ollama model",
        options=["llama3.2:3b (Recommended)", "phi3.5:mini", "qwen2.5:3b", "qwen3:4b", "llama3.2:1b", "gemma2:2b"],
        index=0,
        help="Select a model that's pulled and available locally. Recommended: llama3.2:3b, phi3.5:mini, qwen2.5:3b for speed."
    )
    
    # Extract actual model name (remove recommendation label if present)
    actual_model = model.split(" (")[0] if " (" in model else model

    # Check Ollama status
    ollama_running = check_ollama_status()
    if ollama_running:
        st.markdown("✅ **Ollama Status:** Running at http://localhost:11434")
    else:
        st.markdown("❌ **Ollama Status:** Not running. Please start Ollama.")
        st.caption("Start Ollama from your terminal or application launcher.")
    
    st.markdown("---")
    st.markdown("**Remote Server Connection**")
    
    # Initialize session state for connection
    if "remote_connected" not in st.session_state:
        st.session_state["remote_connected"] = False
    if "remote_ip" not in st.session_state:
        st.session_state["remote_ip"] = ""
    if "remote_username" not in st.session_state:
        st.session_state["remote_username"] = ""
    if "remote_password" not in st.session_state:
        st.session_state["remote_password"] = ""
    
    use_remote = st.checkbox("Enable Remote Log Access", help="Connect to remote server to access log files")
    
    if use_remote:
        col1, col2 = st.columns(2)
        with col1:
            remote_ip = st.text_input("Server IP Address", value=st.session_state.get("remote_ip", ""), placeholder="192.168.1.100")
            remote_username = st.text_input("Username", value=st.session_state.get("remote_username", ""), placeholder="admin")
        with col2:
            remote_password = st.text_input("Password", type="password", placeholder="••••••••")
            test_conn_btn = st.button("Test Connection", use_container_width=True)
        
        if test_conn_btn and remote_ip and remote_username and remote_password:
            with st.spinner("Testing connection..."):
                success, message = test_remote_connection(remote_ip, remote_username, remote_password)
                if success:
                    st.session_state["remote_connected"] = True
                    st.session_state["remote_ip"] = remote_ip
                    st.session_state["remote_username"] = remote_username
                    st.session_state["remote_password"] = remote_password
                    st.success(message)
                else:
                    st.session_state["remote_connected"] = False
                    st.error(message)
        
        # Connection status indicator
        if st.session_state.get("remote_connected", False):
            st.markdown(f"✅ **Remote Status:** Connected to {st.session_state['remote_ip']}")
        else:
            st.markdown("❌ **Remote Status:** Not connected")
    else:
        st.session_state["remote_connected"] = False

# Create tabs for different analysis types
tab1, tab2 = st.tabs(["📄 PSR Report Analysis", "🌐 Apache Log Analysis"])

with tab1:
    st.markdown("### Analyze Jasper Report Logs")
    prompt = st.text_area("Message", placeholder="Find report details from logfile.log or /var/log/report.log (remote)", value="", height=120, key="report_prompt")
    
    run_btn = st.button("Analyze Report", use_container_width=True, type="primary", key="report_btn")
    
    if run_btn and prompt.strip():
        with st.spinner("Analyzing report log..."):
            try:
                # Prepare remote config if enabled
                remote_config = None
                if st.session_state.get("remote_connected", False):
                    remote_config = {
                        "enabled": True,
                        "connected": True,
                        "ip": st.session_state["remote_ip"],
                        "username": st.session_state["remote_username"],
                        "password": st.session_state["remote_password"]
                    }
                
                answer = asyncio.run(ask_with_mcp_tools(prompt.strip(), model=actual_model.strip(), remote_config=remote_config))
                st.session_state["report_answer"] = answer
            except Exception as e:
                st.error(f"Error: {e}")
                st.session_state["report_answer"] = None
    
    # Display report results
    if "report_answer" in st.session_state and st.session_state["report_answer"]:
        st.subheader("Answer")
        answer = st.session_state["report_answer"]
        
        # Try to extract tabular data from report responses
        if "Report Name:" in answer and "Date Range Start:" in answer:
            import re
            report_data = {}
            patterns = {
                "Report Name": r"Report Name:\s*(.+?)(?=\n|File Type:|$)",
                "File Type": r"File Type:\s*(.+?)(?=\n|Schedule Type:|$)",
                "Schedule Type": r"Schedule Type:\s*(.+?)(?=\n|Time Initiated:|$)",
                "Time Initiated": r"Time Initiated:\s*(.+?)(?=\n|Date Range Start:|$)",
                "Date Range Start": r"Date Range Start:\s*(.+?)(?=\n|Date Range End:|$)",
                "Date Range End": r"Date Range End:\s*(.+?)(?=\n|Number of Days:|$)",
                "Number of Days": r"Number of Days:\s*(.+?)(?=\n|Log Line:|$)",
                "Log Line": r"Log Line:\s*(.+?)(?=\n|$)"
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, answer)
                if match:
                    value = match.group(1).strip()
                    value = re.sub(r'\s*\([^)]+\)', '', value)
                    report_data[key] = value
            
            if report_data:
                import pandas as pd
                df = pd.DataFrame([report_data]).T
                df.columns = ["Value"]
                st.table(df)
            else:
                st.write(answer)
        else:
            st.write(answer)

with tab2:
    st.markdown("### Live Apache Log Monitor")
    
    # Initialize session state for live monitoring
    if "monitoring_active" not in st.session_state:
        st.session_state["monitoring_active"] = False
    if "apache_live_data" not in st.session_state:
        st.session_state["apache_live_data"] = None
    if "last_update" not in st.session_state:
        st.session_state["last_update"] = None
    
    # Live monitoring controls
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        log_dir = st.text_input(
            "Apache Logs Directory", 
            value="/niceapps/apacheconf/apache/logs/",
            placeholder="/var/log/apache2/",
            help="Remote directory containing Apache log files"
        )
    
    with col2:
        tail_lines = st.number_input("Lines to tail", min_value=50, max_value=5000, value=500, step=50)
    
    with col3:
        refresh_interval = st.number_input("Refresh (sec)", min_value=5, max_value=300, value=30, step=5)
    
    # Control buttons
    btn_col1, btn_col2, btn_col3 = st.columns(3)
    
    with btn_col1:
        start_monitor = st.button("🔴 Start Live Monitor", use_container_width=True, type="primary", disabled=not st.session_state.get("remote_connected", False))
    
    with btn_col2:
        stop_monitor = st.button("⏹️ Stop Monitor", use_container_width=True, disabled=not st.session_state.get("monitoring_active", False))
    
    with btn_col3:
        manual_refresh = st.button("🔄 Refresh Now", use_container_width=True, disabled=not st.session_state.get("monitoring_active", False))
    
    # Connection warning
    if not st.session_state.get("remote_connected", False):
        st.warning("⚠️ Remote connection required. Please connect to a server in Settings first.")
    
    # Start monitoring
    if start_monitor and st.session_state.get("remote_connected", False):
        with st.spinner("Fetching latest Apache log..."):
            try:
                # Get latest file from directory
                success, result = get_latest_remote_file(
                    st.session_state["remote_ip"],
                    st.session_state["remote_username"],
                    st.session_state["remote_password"],
                    log_dir
                )
                
                if success:
                    latest_file = result
                    st.session_state["latest_log_file"] = latest_file
                    
                    # Tail the file
                    success, local_path = tail_remote_file(
                        st.session_state["remote_ip"],
                        st.session_state["remote_username"],
                        st.session_state["remote_password"],
                        latest_file,
                        tail_lines
                    )
                    
                    if success:
                        # Analyze the tailed log
                        answer = asyncio.run(ask_with_mcp_tools(
                            f"Analyze apache log {local_path}", 
                            model=actual_model.strip(),
                            remote_config=None  # Already downloaded
                        ))
                        st.session_state["apache_live_data"] = answer
                        st.session_state["monitoring_active"] = True
                        st.session_state["last_update"] = asyncio.run(get_current_time_async())
                        st.success(f"✅ Monitoring: {latest_file}")
                    else:
                        st.error(local_path)
                else:
                    st.error(result)
            except Exception as e:
                st.error(f"Error: {e}")
    
    # Stop monitoring
    if stop_monitor:
        st.session_state["monitoring_active"] = False
        st.info("Monitoring stopped")
    
    # Manual refresh
    if manual_refresh and st.session_state.get("monitoring_active", False):
        with st.spinner("Refreshing data..."):
            try:
                latest_file = st.session_state.get("latest_log_file")
                success, local_path = tail_remote_file(
                    st.session_state["remote_ip"],
                    st.session_state["remote_username"],
                    st.session_state["remote_password"],
                    latest_file,
                    tail_lines
                )
                
                if success:
                    answer = asyncio.run(ask_with_mcp_tools(
                        f"Analyze apache log {local_path}", 
                        model=actual_model.strip(),
                        remote_config=None
                    ))
                    st.session_state["apache_live_data"] = answer
                    st.session_state["last_update"] = asyncio.run(get_current_time_async())
                    st.success(f"✅ Refreshed at {st.session_state['last_update']}")
                else:
                    st.error(local_path)
            except Exception as e:
                st.error(f"Error: {e}")
    
    # Auto-refresh logic
    if st.session_state.get("monitoring_active", False):
        from datetime import datetime, timedelta
        
        # Display status
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, #0a0e27 0%, #16213e 100%); padding: 15px; border-radius: 8px; border: 1px solid #00d9ff; margin-bottom: 20px;'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <span style='color: #00ff88; font-size: 18px;'>🟢 LIVE MONITORING</span><br>
                    <span style='color: #b8c5d6; font-size: 12px;'>File: {st.session_state.get('latest_log_file', 'N/A')}</span>
                </div>
                <div style='text-align: right;'>
                    <span style='color: #b8c5d6; font-size: 12px;'>Last Update</span><br>
                    <span style='color: #00d9ff; font-size: 14px;'>{st.session_state.get('last_update', 'N/A')}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Display current data
        if st.session_state.get("apache_live_data"):
            render_apache_analysis(st.session_state["apache_live_data"])
        
        # Check if it's time to refresh
        if "next_refresh_time" not in st.session_state:
            st.session_state["next_refresh_time"] = datetime.now() + timedelta(seconds=refresh_interval)
        
        # Auto-refresh if interval has passed
        if datetime.now() >= st.session_state["next_refresh_time"]:
            try:
                latest_file = st.session_state.get("latest_log_file")
                success, local_path = tail_remote_file(
                    st.session_state["remote_ip"],
                    st.session_state["remote_username"],
                    st.session_state["remote_password"],
                    latest_file,
                    tail_lines
                )
                
                if success:
                    answer = asyncio.run(ask_with_mcp_tools(
                        f"Analyze apache log {local_path}", 
                        model=actual_model.strip(),
                        remote_config=None
                    ))
                    st.session_state["apache_live_data"] = answer
                    st.session_state["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    st.session_state["next_refresh_time"] = datetime.now() + timedelta(seconds=refresh_interval)
            except Exception as e:
                st.error(f"Auto-refresh error: {e}")
        
        # Use st.empty() and rerun for continuous monitoring
        import time
        time.sleep(1)  # Small sleep to prevent overwhelming the system
        st.rerun()
    
    # Display results if monitoring stopped but data exists
    elif st.session_state.get("apache_live_data") and not st.session_state.get("monitoring_active", False):
        st.info(f"📊 Showing last captured data from {st.session_state.get('last_update', 'unknown time')}")
        render_apache_analysis(st.session_state["apache_live_data"])


# Helper function for async time
async def get_current_time_async():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Add Ctrl+Enter functionality
st.markdown("""
<script>
document.addEventListener('DOMContentLoaded', function() {
    const checkAndAddListener = () => {
        const textarea = window.parent.document.querySelector('textarea[aria-label="Message"]');
        if (textarea && !textarea.hasAttribute('data-listener-added')) {
            textarea.setAttribute('data-listener-added', 'true');
            textarea.addEventListener('keydown', function(e) {
                if (e.ctrlKey && e.key === 'Enter') {
                    e.preventDefault();
                    const button = window.parent.document.querySelector('button[kind="primary"]');
                    if (button) {
                        button.click();
                    }
                }
            });
        }
    };
    checkAndAddListener();
    setInterval(checkAndAddListener, 500);
});
</script>
""", unsafe_allow_html=True)