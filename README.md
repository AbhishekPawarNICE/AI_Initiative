# PSR Report AI Tool

A sophisticated AI-powered analysis tool for PSR (Jasper) report logs, built with Streamlit, Ollama, and Model Context Protocol (MCP). Features an elegant dark technical UI with intelligent tool-calling capabilities.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

---

## 🎯 Features

### Core Capabilities
- **Intelligent Report Log Analysis** - Automatically extracts report metadata from Jasper log files
- **AI-Powered Query Interface** - Natural language queries using Ollama LLMs with MCP tool integration
- **Automatic Tool Calling** - Detects file paths and forces tool execution even when model fails to call tools
- **Tabular Data Display** - Clean, structured output in responsive tables with dark theme
- **Multi-Model Support** - Dropdown selection of optimized Ollama models

### Report Analysis Features
Extracts the following from Jasper report logs:
- ✅ Report Name/Type (e.g., TIMEUTIL, SCHEDULE)
- ✅ File Type (PDF, Excel, etc.)
- ✅ Schedule Type (AGENT, SYSTEM)
- ✅ Time Initiated (execution timestamp)
- ✅ Date Range (start date, end date, number of days)
- ✅ Log Line Number (for traceability)

### UI/UX Features
- 🎨 **Dark Technical Theme** - Professional gradient background with cyan/green accents
- 🔄 **Live Ollama Status Check** - Real-time connection indicator (✅/❌)
- ⌨️ **Keyboard Shortcuts** - Ctrl+Enter to submit queries
- 📊 **Responsive Tables** - Bright, visible text on dark backgrounds
- 🎯 **Model Recommendations** - Clear labeling of recommended models
- 🖼️ **Custom Branding** - NiCE logo integration

---

## 📋 Prerequisites

### Required Software
1. **Python 3.10+** - [Download](https://www.python.org/downloads/)
2. **Ollama** - [Download](https://ollama.ai/download)
3. **Git** (optional) - For cloning the repository

### Required Ollama Models
Pull at least one of these models (recommended models marked with ⭐):
```bash
# Recommended models (faster, better tool calling)
ollama pull llama3.2:3b     # ⭐ Default - Best balance
ollama pull phi3.5:mini     # ⭐ Fast and lightweight
ollama pull qwen2.5:3b      # ⭐ Good for structured tasks

# Alternative models
ollama pull qwen3:4b        # Larger, more accurate
ollama pull llama3.2:1b     # Fastest (may have poor tool calling)
ollama pull gemma2:2b       # Google's model
```

---

## 🚀 Installation

### 1. Clone or Download the Project
```bash
git clone <repository-url>
cd AI_Initiative
```

### 2. Install Python Dependencies
```bash
pip install streamlit ollama mcp requests pandas
```

**Complete Dependency List:**
- `streamlit` - Web UI framework
- `ollama` - Ollama Python client for LLM interactions
- `mcp` - Model Context Protocol client/server
- `requests` - HTTP library for Ollama status checks
- `pandas` - Data manipulation for tabular display
- `asyncio` - Async/await support (built-in)
- `re` - Regular expressions (built-in)

### 3. Verify Ollama is Running
```bash
# Start Ollama service (if not already running)
ollama serve

# Test connectivity
curl http://localhost:11434/api/tags
```

### 4. Prepare Your Log Files
Ensure your Jasper report log files are accessible. Example path:
```
C:\Users\<your-user>\Desktop\AI_Initiative\logfile.log
```

---

## 📁 Project Structure

```
AI_Initiative/
├── code.py              # Main Streamlit application
├── server.py            # MCP FastMCP server with tools
├── styles.css           # Custom dark theme styling
├── logfile.log          # Sample Jasper report log
├── NiceLogo.png         # Company logo (optional)
└── README.md            # This file
```

### File Descriptions

**`code.py`** - Streamlit UI application
- Handles user interface and interactions
- Integrates Ollama LLM with MCP tools via STDIO
- Implements automatic tool-calling fallback
- Renders tabular output with custom CSS

**`server.py`** - MCP Tool Server
- Exposes 7 tools via FastMCP framework:
  - `add_numbers` - Basic arithmetic
  - `multiply_numbers` - Basic arithmetic
  - `summarize_text` - Text summarization
  - `count_words` - Word counting
  - `get_current_time` - System time
  - `reverse_text` - String reversal
  - `analyze_report_log` ⭐ - **Main feature: PSR report log analysis**

**`styles.css`** - Custom theming
- Dark gradient background (#0a0e27 → #16213e)
- Cyan (#00d9ff) and green (#00ff88) accent colors
- Table, button, input, and dropdown styling
- Header and logo positioning

---

## 🎮 Usage

### Starting the Application

1. **Start Ollama** (if not running):
   ```bash
   ollama serve
   ```

2. **Launch Streamlit**:
   ```bash
   streamlit run code.py
   ```

3. **Open Browser**:
   - Streamlit will automatically open `http://localhost:8501`
   - Or navigate to the URL shown in the terminal

### Using the Tool

#### Settings Panel
1. **Select Ollama Model** - Choose from the dropdown (llama3.2:3b recommended)
2. **Check Ollama Status** - Verify green ✅ indicator

#### Querying Report Logs

**Example Queries:**
```
Find report details from logfile.log

Analyze the report at C:\path\to\your\logfile.log

What's in the log file?

Show me report information from logfile.log
```

**How It Works:**
1. Type your query in the message box
2. Press **Ask** button or **Ctrl+Enter**
3. System detects file path automatically
4. Calls `analyze_report_log` MCP tool
5. Displays results in a formatted table

#### Sample Output Table
| Field | Value |
|-------|-------|
| Report Name | TIMEUTIL |
| File Type | PDF |
| Schedule Type | AGENT |
| Time Initiated | 2026-02-26 20:37:48,202 |
| Date Range Start | 2025-12-01 |
| Date Range End | 2025-12-31 |
| Number of Days | 31 |
| Log Line | 1 |

---

## 🏗️ Architecture

### Technology Stack
```
┌─────────────────────────────────────┐
│         Streamlit UI (code.py)      │
│  - User Interface                   │
│  - Custom CSS Theming              │
│  - Ollama Integration              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Ollama (localhost:11434)       │
│  - LLM Inference                    │
│  - Tool Calling Protocol            │
│  - Models: llama3.2, phi3.5, etc.  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│    MCP Server (server.py - STDIO)   │
│  - FastMCP Framework                │
│  - Tool: analyze_report_log         │
│  - Regex-based log parsing          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│        Jasper Report Logs           │
│  - Log file parsing                 │
│  - Metadata extraction              │
└─────────────────────────────────────┘
```

### Data Flow
1. User enters query → Streamlit UI
2. System detects file path in query
3. Streamlit spawns MCP server as subprocess (STDIO)
4. Ollama receives query + tool schema
5. **Fallback mechanism**: If model doesn't call tool, force direct call
6. MCP tool parses log file with regex
7. Returns structured key-value pairs
8. Streamlit parses output into table
9. Displays with custom CSS styling

---

## 🎨 Customization

### Changing Theme Colors
Edit `styles.css`:
```css
/* Primary gradient */
background: linear-gradient(135deg, #0a0e27 0%, #16213e 100%);

/* Accent colors */
--cyan: #00d9ff;
--green: #00ff88;
```

### Adding New Models
Edit `code.py`, line ~173:
```python
options=["llama3.2:3b (Recommended)", "your-model:tag", ...]
```

### Adding New MCP Tools
Edit `server.py`, add new tool:
```python
@mcp.tool()
def your_new_tool(param: str) -> str:
    """Your tool description for the LLM"""
    # Your logic here
    return "result"
```

---

## 🐛 Troubleshooting

### Issue: "Ollama Status: ❌ Not running"
**Solution:**
```bash
# Start Ollama service
ollama serve
```

### Issue: Model returns code instead of calling tool
**Solution:** The app has automatic fallback - it will detect file paths and force tool calls. If still failing:
1. Try a different model (llama3.2:3b or phi3.5:mini)
2. Make query more explicit: "Use analyze_report_log tool for logfile.log"

### Issue: Table text not visible
**Solution:**
1. Hard-refresh browser: `Ctrl+F5` (Windows) or `Cmd+Shift+R` (Mac)
2. Clear browser cache
3. Restart Streamlit

### Issue: MCP server fails to start
**Solution:**
```bash
# Test MCP server directly
python server.py
# Should show: "Server running on stdio"
```

### Issue: Dropdown menu has white background
**Solution:** 
1. Ensure `styles.css` is loaded
2. Hard-refresh browser
3. Check console for CSS errors

---

## 🔧 Development

### Debug Mode
Enable debug output in `code.py` - already enabled:
```python
print(f"[DEBUG] Model didn't call tool. Using fallback...")
print(f"[DEBUG] MCP Tool Result: {content_str[:200]}")
```
Check Streamlit terminal for debug logs.

### Testing MCP Tool Directly
```bash
# Run server in isolation
python server.py

# In another terminal, test with mcp CLI
mcp call analyze_report_log '{"log_file_path": "logfile.log"}'
```

---

## 📊 Performance

### Recommended Models by Speed
| Model | Speed | Quality | Tool Calling | Recommended |
|-------|-------|---------|--------------|-------------|
| llama3.2:1b | ⚡⚡⚡ | ⭐⭐ | ❌ Poor | ❌ |
| gemma2:2b | ⚡⚡⚡ | ⭐⭐⭐ | ✅ Fair | ✅ |
| llama3.2:3b | ⚡⚡ | ⭐⭐⭐⭐ | ✅ Good | ⭐ Best |
| phi3.5:mini | ⚡⚡ | ⭐⭐⭐⭐ | ✅ Good | ⭐ Best |
| qwen2.5:3b | ⚡⚡ | ⭐⭐⭐⭐ | ✅ Good | ⭐ Best |
| qwen3:4b | ⚡ | ⭐⭐⭐⭐⭐ | ✅ Excellent | ✅ |

### Typical Response Times
- Simple queries: 1-3 seconds
- Tool calling: 2-5 seconds
- With MCP startup: 3-7 seconds (first query only)

---

## 🛣️ Roadmap / Future Features

- [ ] **Batch Log Analysis** - Process multiple log files at once
- [ ] **Apache Log Analysis** - New tool for Apache access logs
- [ ] **Performance Dashboard** - Visualize response times, error rates
- [ ] **Export to CSV/Excel** - Download analysis results
- [ ] **Report Search** - Find specific reports by name/date
- [ ] **Failed Report Detector** - Identify errors in logs
- [ ] **Conversation History** - Remember previous queries in session
- [ ] **Real-time Log Monitoring** - Watch logs as they're written

---

## 📝 License

MIT License - See LICENSE file for details

---

## 👥 Support

For issues or questions:
1. Check the **Troubleshooting** section above
2. Review debug logs in Streamlit terminal
3. Verify Ollama is running: `http://localhost:11434`
4. Contact: [Your contact info]

---

## 🙏 Acknowledgments

- **Streamlit** - Modern web UI framework
- **Ollama** - Local LLM inference
- **FastMCP** - Model Context Protocol implementation
- **NiCE Ltd** - Logo and branding

---

**Built with ❤️ for efficient PSR report analysis**
