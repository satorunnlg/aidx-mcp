"""MCPサーバーの手動テストスクリプト"""
import json
import subprocess
import sys

# MCPサーバーを起動
python_exe = r"C:\Users\kisar\github\aidx-mcp\.venv\Scripts\python.exe"
main_py = r"C:\Users\kisar\github\aidx-mcp\client\mcp-server\src\main.py"

env = {
    "AIDX_CAD_TYPE": "fusion360",
    "AIDX_PORT": "8109"
}

print("Starting MCP server...")
proc = subprocess.Popen(
    [python_exe, main_py],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env={**dict(subprocess.os.environ), **env},
    text=True,
    bufsize=0
)

# 1. Initialize request
init_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0"}
    }
}

print("\n=== Sending initialize request ===")
print(json.dumps(init_request))
proc.stdin.write(json.dumps(init_request) + "\n")
proc.stdin.flush()

# Read response
response = proc.stdout.readline()
print("\n=== Initialize response ===")
print(response)

# 2. Tools list request
tools_request = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list"
}

print("\n=== Sending tools/list request ===")
print(json.dumps(tools_request))
proc.stdin.write(json.dumps(tools_request) + "\n")
proc.stdin.flush()

# Read response
response = proc.stdout.readline()
print("\n=== Tools list response ===")
print(response)

# Read stderr
import threading
def read_stderr():
    for line in proc.stderr:
        print(f"[STDERR] {line}", end="")

stderr_thread = threading.Thread(target=read_stderr, daemon=True)
stderr_thread.start()

print("\n=== Press Enter to terminate ===")
input()

proc.terminate()
proc.wait()
