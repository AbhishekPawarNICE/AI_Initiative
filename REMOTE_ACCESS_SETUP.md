# Remote Log Access Setup

## Overview
The PSR Report AI Tool now supports accessing log files from remote servers via SSH/SFTP connection.

## Installation

Install the required dependency for remote access:

```bash
pip install paramiko
```

## How to Use

1. **Enable Remote Access**: In the Settings panel, check the "Enable Remote Log Access" checkbox

2. **Configure Connection**:
   - Enter the remote server IP address (e.g., `192.168.1.100`)
   - Enter your SSH username (e.g., `admin`)
   - Enter your SSH password

3. **Test Connection**: Click the "Test Connection" button to verify connectivity
   - ✅ Green checkmark = Connection successful
   - ❌ Red X = Connection failed (check credentials and network)

4. **Analyze Remote Logs**: Once connected, you can reference remote log files in your queries:
   - **Linux paths**: `/var/log/apache2/access.log`
   - **Windows paths**: `C:\logs\report.log`
   - **Relative paths**: `apache_access.log` (from user's home directory)

## Examples

### PSR Report Analysis (Remote)
```
Analyze /opt/jasper/logs/report_2024.log
```

### Apache Log Analysis (Remote)
```
Analyze performance metrics from /var/log/apache2/access.log
```

## Security Notes

- Credentials are stored in session state only (not persisted)
- Connection is established per analysis request
- Use strong passwords and consider SSH key authentication for production
- Firewall must allow SSH (port 22) access from your machine to the remote server

## Troubleshooting

**Connection Failed**: 
- Verify IP address is correct and server is reachable
- Check username and password are valid
- Ensure SSH service is running on remote server
- Verify firewall allows SSH connections

**File Not Found**:
- Use absolute paths for remote files
- Verify the file exists on the remote server
- Check file permissions allow read access

**paramiko Not Installed**:
- Run: `pip install paramiko`
- Restart the Streamlit application
