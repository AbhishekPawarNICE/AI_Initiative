# server.py
from mcp.server.fastmcp import FastMCP
from datetime import datetime
import re
from typing import Dict, List, Optional

# Create MCP server
mcp = FastMCP("Sample MCP Server Tools")


# ------------------ TOOL 1: ADDITION ------------------
@mcp.tool()
def add_numbers(a: float, b: float) -> float:
    """Add two numbers and return the result."""
    return a + b

# ------------------ TOOL 2: MULTIPLICATION ------------------
@mcp.tool()
def multiply_numbers(a: float, b: float) -> float:
    """Multiply two numbers and return the result."""
    return a * b

# ------------------ TOOL 3: TEXT SUMMARY ------------------
@mcp.tool()
def summarize_text(text: str) -> str:
    """Return a short summary of the given text."""
    if len(text) < 50:
        return text
    return text[:50] + "..."

# ------------------ TOOL 4: WORD COUNT ------------------
@mcp.tool()
def count_words(text: str) -> int:
    """Count the number of words in the given text."""
    return len(text.split())

# ------------------ TOOL 5: CURRENT TIME ------------------
@mcp.tool()
def get_current_time() -> str:
    """Get the current system time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ------------------ TOOL 6: REVERSE STRING ------------------
@mcp.tool()
def reverse_text(text: str) -> str:
    """Reverse the given text."""
    return text[::-1]

# ------------------ TOOL 7: REPORT LOG ANALYZER ------------------
@mcp.tool()
def analyze_report_log(log_file_path: str) -> str:
    """
    Extract and analyze PSR report details from Jasper log files. Use this tool whenever the user asks about:
    - Report information, details, or metadata from a log file
    - Finding report names, types, schedules, or dates
    - Analyzing .log files containing report execution data
    - Getting report statistics like date ranges, file types, or execution times
    
    This tool parses log files and extracts:
    - Report name/type (e.g., TIMEUTIL, SCHEDULE, etc.)
    - File type (PDF, Excel, etc.)
    - Schedule type (AGENT, SYSTEM, etc.)
    - Time initiated (when the report started)
    - Date range (start date, end date, number of days)
    - Log line number
    
    Args:
        log_file_path: Full path to the .log file to analyze (e.g., C:\\logs\\report.log)
    
    Returns:
        A formatted string with all extracted report details
    """
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        reports = []
        
        # Pattern to match log timestamp
        timestamp_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})'
        
        # Pattern to extract report type and scheduled name
        report_type_pattern = r'ReportType=(\w+)'
        scheduled_name_pattern = r'scheduledReportName[=\s]*([^,\]]+)'
        report_file_type_pattern = r'reportFileType=(\w+)'
        schedule_type_pattern = r'scheduleReportType=(\w+)'
        
        # Pattern to extract date range
        date_range_pattern = r'DateRange\[start=(\d{4}-\d{2}-\d{2}), end=(\d{4}-\d{2}-\d{2}), #days=(\d+)\]'
        
        # Split log into lines
        lines = log_content.strip().split('\n')
        
        for i, line in enumerate(lines):
            # Find timestamp
            timestamp_match = re.search(timestamp_pattern, line)
            if not timestamp_match:
                continue
                
            timestamp = timestamp_match.group(1)
            
            # Extract report details
            report_type_match = re.search(report_type_pattern, line)
            scheduled_name_match = re.search(scheduled_name_pattern, line)
            file_type_match = re.search(report_file_type_pattern, line)
            schedule_type_match = re.search(schedule_type_pattern, line)
            date_range_match = re.search(date_range_pattern, line)
            
            if report_type_match:
                report_info = {
                    'timestamp': timestamp,
                    'report_type': report_type_match.group(1),
                    'report_name': scheduled_name_match.group(1).strip() if scheduled_name_match else 'N/A',
                    'file_type': file_type_match.group(1) if file_type_match else 'N/A',
                    'schedule_type': schedule_type_match.group(1) if schedule_type_match else 'N/A',
                    'line_number': i + 1
                }
                
                # Extract date range information
                if date_range_match:
                    report_info['date_range_start'] = date_range_match.group(1)
                    report_info['date_range_end'] = date_range_match.group(2)
                    report_info['date_range_days'] = date_range_match.group(3)
                else:
                    report_info['date_range_start'] = 'N/A'
                    report_info['date_range_end'] = 'N/A'
                    report_info['date_range_days'] = 'N/A'
                
                reports.append(report_info)
        
        # Format output
        if not reports:
            return "No report information found in the log file."
        
        result = []
        for idx, report in enumerate(reports, 1):
            result.append(f"=== Report {idx} ===")
            result.append(f"Report Name: {report['report_type']}")
            result.append(f"File Type: {report['file_type']}")
            result.append(f"Schedule Type: {report['schedule_type']}")
            result.append(f"Time Initiated: {report['timestamp']}")
            result.append(f"Date Range Start: {report['date_range_start']}")
            result.append(f"Date Range End: {report['date_range_end']}")
            result.append(f"Number of Days: {report['date_range_days']}")
            result.append(f"Log Line: {report['line_number']}")
            result.append("")
        
        return "\n".join(result)
        
    except FileNotFoundError:
        return f"Error: Log file not found at path: {log_file_path}"
    except Exception as e:
        return f"Error analyzing log file: {str(e)}"

# Run the MCP server
if __name__ == "__main__":
    mcp.run()