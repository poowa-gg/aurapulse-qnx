import http.server
import json
import os
import socketserver
import subprocess
import threading
import time

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

latest_telemetry = {
    "state": "CONNECTING",
    "cycles": 0,
    "clamps": 0,
    "watchdog_trips": 0,
    "ai_silence_ms": 0,
    "req": [0.0, 0.0],
    "safe": [0.0, 0.0],
    "jitter_us": {"last": 0.0, "avg": 0.0, "max": 0.0}
}

control_lock = threading.Lock()
control_proc = None

def get_control_shell():
    global control_proc
    if control_proc is None or control_proc.poll() is not None:
        control_proc = subprocess.Popen(
            ["ssh", "-T", "qnx-qemu", "/bin/sh"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True
        )
    return control_proc

def send_qnx_cmd(remote_cmd):
    global control_proc
    print(f"[Bridge -> QNX] {remote_cmd}")
    with control_lock:
        for attempt in range(2):
            try:
                shell = get_control_shell()
                shell.stdin.write(remote_cmd + "\n")
                shell.stdin.flush()
                return True
            except Exception as e:
                print(f"[Bridge Reconnecting] {e}")
                control_proc = None
        return False

def poll_qnx_telemetry():
    global latest_telemetry
    send_qnx_cmd("pidin | grep -q aurasentry || (/tmp/aurasentry </dev/null >/dev/null 2>&1 &)")

    cmd = [
        "ssh", "qnx-qemu",
        "while true; do cat /dev/aurasentry 2>/dev/null || echo '{\"state\":\"SENTRY_OFFLINE\"}'; sleep 0.08; done"
    ]
    while True:
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            for line in proc.stdout:
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    parsed = json.loads(line)
                    if "cycles" in parsed:
                        latest_telemetry = parsed
                    else:
                        latest_telemetry["state"] = parsed.get("state", "SENTRY_OFFLINE")
        except Exception as e:
            print(f"[Telemetry Poll Warning] {e}")
            latest_telemetry["state"] = "DISCONNECTED"
        time.sleep(1)

class AuraHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        if self.path == "/api/telemetry":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(json.dumps(latest_telemetry).encode("utf-8"))
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/inject/"):
            action = self.path.split("/")[-1]
            if action == "normal":
                qnx_cmd = "slay -f ai_sim 2>/dev/null; /tmp/ai_sim --duration 20 </dev/null >/dev/null 2>&1 &"
            elif action == "hallucinate":
                qnx_cmd = "slay -f ai_sim 2>/dev/null; /tmp/ai_sim --hallucinate --duration 12 </dev/null >/dev/null 2>&1 &"
            elif action == "cpuhog":
                qnx_cmd = "slay -f ai_sim 2>/dev/null; /tmp/ai_sim --cpu-hog --duration 12 </dev/null >/dev/null 2>&1 &"
            elif action == "crash":
                qnx_cmd = "slay -f ai_sim 2>/dev/null"
            elif action == "restart_sentry":
                qnx_cmd = "slay -f aurasentry ai_sim 2>/dev/null; /tmp/aurasentry </dev/null >/dev/null 2>&1 &"
            else:
                self.send_response(400)
                self.end_headers()
                return

            ok = send_qnx_cmd(qnx_cmd)
            self.send_response(200 if ok else 500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok" if ok else "error", "action": action}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    t = threading.Thread(target=poll_qnx_telemetry, daemon=True)
    t.start()
    print(f"[AuraPulse Bridge] Ready at http://localhost:{PORT}")
    with socketserver.ThreadingTCPServer(("", PORT), AuraHandler) as httpd:
        httpd.serve_forever()
