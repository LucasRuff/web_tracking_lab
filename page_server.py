from http.server import SimpleHTTPRequestHandler, HTTPServer
import os

class PageHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.path = "index.html"
        return super().do_GET()

if __name__ == "__main__":
    port = 8080
    server = HTTPServer(("0.0.0.0", port), PageHandler)
    print(f"Page server running at http://0.0.0.0:{port}")
    server.serve_forever()