# Apache Log Analyzer Tool - to be added to server.py

@mcp.tool()
def analyze_apache_log(log_file_path: str, max_lines: int = 1000) -> str:
    """
    Analyze Apache access logs and extract performance metrics, traffic patterns, and error statistics.
    Use this whenever users ask about Apache/web server logs, performance, errors, or traffic patterns.
    
    Args:
        log_file_path: Path to the Apache access log file
        max_lines: Maximum number of lines to analyze (default 1000)
    
    Returns:
        JSON string with metrics, status codes, top endpoints, slow requests
    """
    import json
    from collections import Counter
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            lines = []
            for _ in range(max_lines):
                line = f.readline()
                if not line:
                    break
                lines.append(line)
        
        # Parse Apache log format
        pattern = r'(\d+\.\d+\.\d+\.\d+)\s+\[([^\]]+)\]\s+(\d+)\s+"(\w+)\s+([^"]+)"\s+(\d+)\s+(\d+|-).*?Host=([^\s]+)'
        
        requests = []
        for line in lines:
            match = re.search(pattern, line)
            if match:
                ip, timestamp, response_time, method, endpoint, status, size, host = match.groups()
                requests.append({
                    'ip': ip,
                    'response_time': int(response_time),
                    'endpoint': endpoint.split('?')[0].split(' ')[0],
                    'status': int(status),
                })
        
        if not requests:
            return json.dumps({"error": "No valid Apache log entries found"})
        
        response_times = [r['response_time'] for r in requests]
        statuses = [r['status'] for r in requests]
        endpoints = [r['endpoint'] for r in requests]
        
        avg_response = sum(response_times) / len(response_times)
        p95_response = sorted(response_times)[int(len(response_times) * 0.95)]
        
        status_counter = Counter(statuses)
        status_2xx = sum(count for status, count in status_counter.items() if 200 <= status < 300)
        status_4xx = sum(count for status, count in status_counter.items() if 400 <= status < 500)
        status_5xx = sum(count for status, count in status_counter.items() if 500 <= status < 600)
        
        endpoint_counter = Counter(endpoints)
        top_endpoints = endpoint_counter.most_common(10)
        
        error_rate = ((status_4xx + status_5xx) / len(requests) * 100)
        
        ip_counter = Counter([r['ip'] for r in requests])
        top_ips = ip_counter.most_common(5)
        
        result = {
            "summary": {
                "total_requests": len(requests),
                "avg_response_time_ms": round(avg_response, 2),
                "p95_response_time_ms": p95_response,
                "error_rate_percent": round(error_rate, 2)
            },
            "status_codes": {
                "success_2xx": status_2xx,
                "client_error_4xx": status_4xx,
                "server_error_5xx": status_5xx
            },
            "top_endpoints": [{"endpoint": ep, "count": count} for ep, count in top_endpoints],
            "top_ips": [{"ip": ip, "count": count} for ip, count in top_ips],
            "response_time_dist": {
                "under_1s": sum(1 for rt in response_times if rt < 1000),
                "1_to_5s": sum(1 for rt in response_times if 1000 <= rt < 5000),
                "5_to_10s": sum(1 for rt in response_times if 5000 <= rt < 10000),
                "over_10s": sum(1 for rt in response_times if rt >= 10000)
            }
        }
        
        return json.dumps(result, indent=2)
        
    except FileNotFoundError:
        return json.dumps({"error": f"File not found: {log_file_path}"})
    except Exception as e:
        return json.dumps({"error": f"Error: {str(e)}"})
