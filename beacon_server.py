from http.server import BaseHTTPRequestHandler, HTTPServer
import uuid
import time
import os
from urllib.parse import urlparse, parse_qs
import threading

logs = {}
logs_lock = threading.Lock()

def get_sorted_logs():
    return sorted(logs.items(), key=lambda x: x[1]["count"], reverse=True)

# HTTP handler
class BeaconHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/logs":
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
                    const res = await fetch("/ai105/logs/data");
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
            html.append("<table border='1' cellpadding='5'><tr><th>Visitor ID</th><th>Last Timestamp</th><th>Total Beacons</th><th>Longest Hover (ms)</th></tr>")
            for visitor_id, data in sorted_logs:
                html.append(f"<tr><td>{visitor_id}</td><td>{data['last']}</td><td>{data['count']}</td><td>{data['hover']}</td></tr>")
            html.append("</table>")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("".join(html).encode("utf-8"))
            
        elif self.path.startswith("/instructor-solution"):
            try:
                with open("index.html", "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Dynamically determine the server URL from the Host header
                host = self.headers.get("Host", "localhost:8080")
                # Determine if we should use https (check for common indicators)
                forwarded_proto = self.headers.get("X-Forwarded-Proto", "")
                if forwarded_proto == "https" or host.endswith(".run.app") or host.endswith(".cloud.run"):
                    scheme = "https"
                else:
                    scheme = "http"
                server_url = f"{scheme}://{host}"
                
                # Replace placeholder with actual server URL
                content = content.replace("{{SERVER_URL}}", server_url)
                
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"index.html not found")

        elif self.path == "/script.js":
            query = urlparse(self.path).query
            params = parse_qs(query)
            origin = params.get("origin", ["*"])[0]
            # Bootstrap JS
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.end_headers()
            js = r"""
            (function() {
                // --- 1. Ensure we have a user ID ---
                let uid = localStorage.getItem("third_party_id");
                if (!uid) {
                    uid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
                        const r = Math.random() * 16 | 0;
                        const v = c === 'x' ? r : (r & 0x3 | 0x8);
                        return v.toString(16);
                    });
                    localStorage.setItem("third_party_id", uid);
                }

                // --- 2. Discover server base URL from this script's src ---
                const scriptUrl = document.currentScript.src;
                const serverBase = scriptUrl.substring(0, scriptUrl.lastIndexOf("/"));

                // --- 3. Determine the running page's URL to include as query param ---
                const origin = window.location.origin;

                // --- 4. Request widget (HTML + JS) ---
                fetch(serverBase + "/hover-widget?third_party_id=" + encodeURIComponent(uid) + "&origin=" + encodeURIComponent(origin), {
                    credentials: "include"
                })
                .then(r => r.text())
                .then(html => {
                    const container = document.createElement("div");
                    container.innerHTML = html;

                    document.body.appendChild(container);

                    // Pass serverBase to widget scripts via global variable
                    const script = document.createElement("script");
                    script.textContent = `window.SERVER_BASE = "${serverBase}";`;
                    container.appendChild(script);

                    // Execute all other <script> tags in the widget
                    container.querySelectorAll("script").forEach(oldScript => {
                        if (oldScript === script) return; // skip the SERVER_BASE injector
                        const newScript = document.createElement("script");
                        if (oldScript.src) {
                            newScript.src = oldScript.src;
                        } else {
                            newScript.textContent = oldScript.textContent;
                        }
                        document.body.appendChild(newScript);
                        oldScript.remove();
                    });

                    
                });
            })();
            """
            self.wfile.write(js.encode("utf-8"))

        elif self.path.startswith("/hover-widget"):
            # Extract visitor ID from query
            query = urlparse(self.path).query
            params = parse_qs(query)
            visitor_id = params.get("third_party_id", [None])[0]
            origin = params.get("origin", ["*"])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            if visitor_id:
                self.send_header("Set-Cookie", f"third_party_id={visitor_id}; Path=/; SameSite=None; Secure;")
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.end_headers()

            html = f"""
            <div class="card"><div id="hover-square" style="width:100px;height:100px;background:red;margin:20px;"></div></div>
            <script>
            (function() {{
                const square = document.getElementById("hover-square");
                const visitorId = "{visitor_id}";
                const serverBase = window.SERVER_BASE;
                let hoverStart = null;

                square.addEventListener("mouseenter", () => {{
                    hoverStart = Date.now();
                }});

                square.addEventListener("mouseleave", () => {{
                    if (hoverStart !== null) {{
                        const duration = Date.now() - hoverStart;
                        const origin = window.location.origin;
                        fetch(`${{serverBase}}/hover-beacon?third_party_id=${{encodeURIComponent(visitorId)}}&duration=${{duration}}&origin=${{encodeURIComponent(origin)}}`, {{
                            method: "GET",
                            credentials: "include"
                        }});
                        hoverStart = null;
                    }}
                }});
            }})();
            </script>
            """
            self.wfile.write(html.encode("utf-8"))

        elif self.path.startswith("/hover-beacon"):
            query = urlparse(self.path).query
            params = parse_qs(query)
            visitor_id = params.get("third_party_id", [None])[0]
            origin = params.get("origin", ["*"])[0]
            had_visitor_id = (visitor_id!=None)

            #look for vid in query params first; look for a cookie if not sent in query param
            if not visitor_id:
                cookie_header = self.headers.get("Cookie")
                if cookie_header:
                    try:
                        cookies = dict(cookie.split("=", 1) for cookie in cookie_header.split("; "))
                        visitor_id = cookies.get("third_party_id")
                    except:
                        pass

            if not visitor_id:
                visitor_id = str(uuid.uuid4())

            duration = float(params.get("duration", [0])[0])
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

            if visitor_id not in logs:
                with logs_lock:
                    logs[visitor_id] = {"last": timestamp, "count": 1, "hover": duration}
            else:
                with logs_lock:
                    logs[visitor_id]["last"] = timestamp
                    logs[visitor_id]["count"] += 1
                    if duration > logs[visitor_id]["hover"]:
                        logs[visitor_id]["hover"] = duration

            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            if not had_visitor_id:
                self.send_header("Set-Cookie", f"third_party_id={visitor_id}; Path=/; SameSite=None; Secure;")
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Credentials", "true")
            self.end_headers()
            self.wfile.write(b"OK")

        else:
            self.send_response(404)
            self.end_headers()

def clear_logs_periodically():
    while True:
        time.sleep(3600)
        with logs_lock:
            logs.clear()

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 8080))

    threading.Thread(target=clear_logs_periodically, daemon=True).start()
    server = HTTPServer(("0.0.0.0", PORT), BeaconHandler)
    print(f"Beacon server running at http://0.0.0.0:{PORT}")
    server.serve_forever()
    clear_logs_periodically()