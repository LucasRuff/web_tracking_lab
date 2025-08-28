from http.server import SimpleHTTPRequestHandler, HTTPServer
import os

class PageHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.path = "index.html"
            return super().do_GET()
        elif self.path.startswith("/hover-beacon") or self.path.startswith("/beacon"):
            self.send_response(200)
            self.send_header("content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    port = 8080
    server = HTTPServer(("0.0.0.0", port), PageHandler)
    print(f"Page server running at http://0.0.0.0:{port}")
    server.serve_forever()