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
from pathlib import Path


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


# ---- Core: ask the LLM, let it call MCP tools, return final text ----
async def ask_with_mcp_tools(question: str, model: str = "qwen3:4b"):
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
            file_path_match = regex_module.search(r'[A-Za-z]:\\[^\s]+\.log|logfile\.log', question)
            
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
            if file_path_match:
                user_content = f"Use the analyze_report_log tool to analyze: {file_path_match.group(0)}"
            
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
            if not tool_calls and file_path_match:
                # DEBUG: Log that we're using fallback
                print(f"[DEBUG] Model didn't call tool. Using fallback to call analyze_report_log with: {file_path_match.group(0)}")
                
                # Manually construct tool call
                tool_result = await session.call_tool("analyze_report_log", {"log_file_path": file_path_match.group(0)})
                
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

prompt = st.text_area("Message", placeholder="How can I help you today?", value="", height=120, key="user_prompt")

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
                    const button = window.parent.document.querySelector('button[kind="primary"]') || 
                                   Array.from(window.parent.document.querySelectorAll('button')).find(btn => btn.innerText.includes('Ask'));
                    if (button) {
                        button.click();
                    }
                }
            });
        }
    };
    
    // Initial check
    checkAndAddListener();
    
    // Keep checking in case textarea is recreated
    setInterval(checkAndAddListener, 500);
});
</script>
""", unsafe_allow_html=True)

run_btn = st.button("Ask", use_container_width=True, type="primary")

if run_btn and prompt.strip():
    with st.spinner("Thinking (may start the MCP server)…"):
        try:
            answer = asyncio.run(ask_with_mcp_tools(prompt.strip(), model=actual_model.strip()))
            st.session_state["answer"] = answer
            st.session_state["last_prompt"] = prompt.strip()
        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state["answer"] = None

if "answer" in st.session_state and st.session_state["answer"]:
    st.subheader("Answer")
    
    # Check if the answer contains report data in structured format
    answer = st.session_state["answer"]
    
    # Try to extract tabular data from report responses
    if "Report Name:" in answer and "Date Range Start:" in answer:
        # Parse the report data into a table
        import re
        
        # Extract key-value pairs
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
                # Remove parenthetical explanations
                value = re.sub(r'\s*\([^)]+\)', '', value)
                report_data[key] = value
        
        # Display as table if we found data
        if report_data:
            import pandas as pd
            df = pd.DataFrame([report_data]).T
            df.columns = ["Value"]
            st.table(df)
            
            # Show any additional text below
            additional_text = re.split(r'Log Line:\s*[^\n]+', answer, 1)
            if len(additional_text) > 1 and additional_text[1].strip():
                st.write("---")
                st.write(additional_text[1].strip())
        else:
            st.write(answer)
    else:
        st.write(answer)