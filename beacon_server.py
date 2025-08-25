#!/usr/bin/env python3
from http.server import BaseHTTPRequestHandler, HTTPServer
import uuid
import time
from urllib.parse import urlparse, parse_qs

logs = {}

def get_sorted_logs():
    return sorted(logs.items(), key=lambda x: x[1]["count"], reverse=True)

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

            # --- 3. Log beacon info ---
            query = urlparse(self.path).query
            params = parse_qs(query)
            hover_length = float(params.get("duration", [0])[0])
            timestamp = params.get("ts", [time.strftime("%Y-%m-%d %H:%M:%S")])[0]
            if visitor_id not in logs:
                logs[visitor_id] = {"last": timestamp, "count": 1, "hover": hover_length}
            else:
                logs[visitor_id]["last"] = timestamp
                logs[visitor_id]["count"] += 1
                if hover_length > logs[visitor_id]["hover"]:
                    logs[visitor_id]["hover"] = hover_length

            # --- 4. Send response with cookie ---
            self.send_response(200)
            self.send_header("Content-Type", "image/gif")
            self.send_header("Set-Cookie", f"visitor_id={visitor_id}; Path=/")  # session cookie
            self.end_headers()

            # Transparent 1x1 GIF tracking pixel
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
            # Serve only the table HTML
            sorted_logs = get_sorted_logs()
            html = []
            html.append("<table border='1' cellpadding='5'><tr><th>Visitor ID</th><th>Last Timestamp</th><th>Total Beacons</th><th>Longest Hover</th></tr>")
            for visitor_id, data in sorted_logs:
                html.append(f"<tr><td>{visitor_id}</td><td>{data['last']}</td><td>{data['count']}</td><td>{data['hover']}</td></tr>")
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

    server = HTTPServer(("0.0.0.0", PORT), BeaconHandler)
    print(f"Beacon server running at http://0.0.0.0:{PORT}")
    server.serve_forever()
