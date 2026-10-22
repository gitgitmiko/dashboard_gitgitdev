#!/usr/bin/env python3
"""Serves dist/ on 127.0.0.1 for the Cloudflare tunnel (Python standard library only).

    python3 serve.py [--port 8796]

www.<domain> is redirected to the bare domain; unknown paths get dist/404.html.
"""
import argparse
import functools
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")


class Handler(SimpleHTTPRequestHandler):
    server_version = "gitgitdev"
    sys_version = ""
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      ".txt": "text/plain; charset=utf-8", ".webp": "image/webp", ".svg": "image/svg+xml",
                      ".xml": "application/xml; charset=utf-8", ".html": "text/html; charset=utf-8"}

    def send_head(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        if host.startswith("www."):
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header("Location", "https://" + host[4:] + self.path)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        path = self.translate_path(self.path)
        if not os.path.exists(path):
            return self.not_found()
        return super().send_head()

    def not_found(self):
        page = os.path.join(DIST, "404.html")
        body = open(page, "rb").read() if os.path.isfile(page) else b"Not found"
        self.send_response(HTTPStatus.NOT_FOUND)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        return None

    def list_directory(self, path):
        return self.not_found()

    def end_headers(self):
        cacheable = "/assets/" in self.path or self.path.startswith("/static/")
        self.send_header("Cache-Control", "public, max-age=86400" if cacheable else "public, max-age=300")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8796)
    args = parser.parse_args()
    handler = functools.partial(Handler, directory=DIST)
    with ThreadingHTTPServer((args.host, args.port), handler) as server:
        print(f"Serving {DIST} on http://{args.host}:{args.port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
