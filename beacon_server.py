#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import sqlite3
import uuid
import time
import threading

DB_FILE = "visitor_logs.db"
BATCH_SIZE = 10           # Number of beacons to batch before writing
FLUSH_INTERVAL = 5        # Seconds to flush batch if not full

# In-memory batch queue
pending_beacons = []
batch_lock = threading.Lock()

# Initialize SQLite DB
def init_db():
    global conn
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")  # Enable concurrent reads/writes
    conn.execute("""
        CREATE TABLE IF NOT EXISTS beacons (
            visitor_id TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()

# Add beacon to batch
def queue_beacon(visitor_id, timestamp):
    with batch_lock:
        pending_beacons.append((visitor_id, timestamp))
        if len(pending_beacons) >= BATCH_SIZE:
            flush_beacons_locked()

# Flush batch to SQLite
def flush_beacons_locked():
    global pending_beacons
    if not pending_beacons:
        return
    
    cursor = conn.cursor()
    cursor.executemany("INSERT INTO beacons (visitor_id, timestamp) VALUES (?, ?)", pending_beacons)
    conn.commit()
    pending_beacons.clear()

# Periodic flush
def periodic_flush():
    while True:
        time.sleep(FLUSH_INTERVAL)
        with batch_lock:
            flush_beacons_locked()

# Get all logs for /logs/data endpoint
def get_logs():
    
    cursor = conn.cursor()
    cursor.execute("""
                   SELECT visitor_id, timestamp
                   FROM beacons 
                   ORDER BY visitor_id, timestamp
                   """)
    rows = cursor.fetchall()
    logs = {}
    for visitor_id, timestamp in rows:
        if visitor_id not in logs:
            logs[visitor_id] = {"last": timestamp, "count": 1}
        else:
            logs[visitor_id]["last"] = timestamp
            logs[visitor_id]["count"] += 1
    sorted_logs = sorted(logs.items(), key=lambda x: x[1]["count"], reverse=True)
    return sorted_logs

# HTTP handler
class BeaconHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/beacon") or self.path.startswith("/hover-beacon"):
            visitor_id = None

            # --- 1. Check for cookie ---
            cookie_header = self.headers.get("Cookie")
            if cookie_header:
                cookies = dict(cookie.split("=", 1) for cookie in cookie_header.split("; "))
                visitor_id = cookies.get("visitor_id")

            # --- 2. If no cookie, assign unique ID ---
            if not visitor_id:
                visitor_id = str(uuid.uuid4())
                print(f"New visitor assigned ID: {visitor_id}")

            # --- 3. Log beacon timestamp ---
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            queue_beacon(visitor_id, timestamp)
            print(f"Beacon from {visitor_id} at {timestamp}")

            # --- 4. Send response with cookie ---
            self.send_response(200)
            self.send_header("Content-Type", "image/gif")
            self.send_header("Set-Cookie", f"visitor_id={visitor_id}; Path=/")  # session cookie
            self.end_headers()

            # Transparent 1x1 GIF
            gif_data = (
                b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00"
                b"\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00"
                b"\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
            )
            self.wfile.write(gif_data)

        elif self.path == "/logs":
            # Serve full HTML page with JS fetch
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = """
            <html>
            <head><title>Beacon Logs</title></head>
            <body>
                <h1>Beacon Logs</h1>
                <div id="logContainer"></div>
                <script>
                async function updateLogs() {
                    const res = await fetch("/logs/data");
                    const tableHtml = await res.text();
                    document.getElementById("logContainer").innerHTML = tableHtml;
                }
                setInterval(updateLogs, 10000);
                updateLogs();
                </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode("utf-8"))

        elif self.path.startswith("/logs/data"):
            print("Updating log table")
            # Serve only the table HTML
            with batch_lock:
                flush_beacons_locked()
            print("Flushed beacons, fetching logs")
            logs = get_logs()  # e.g., last timestamp + total count
            print("Building HTML table")
            html = []
            html.append("<table border='1' cellpadding='5'><tr><th>Visitor ID</th><th>Last Timestamp</th><th>Total Beacons</th></tr>")
            for visitor_id, data in logs:
                html.append(f"<tr><td>{visitor_id}</td><td>{data['last']}</td><td>{data['count']}</td></tr>")
            html.append("</table>")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("".join(html).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    PORT = 8081
    init_db()

    # Start periodic flush thread
    flush_thread = threading.Thread(target=periodic_flush, daemon=True)
    flush_thread.start()

    server = HTTPServer(("0.0.0.0", PORT), BeaconHandler)
    print(f"Beacon server running at http://0.0.0.0:{PORT}")
    server.serve_forever()
