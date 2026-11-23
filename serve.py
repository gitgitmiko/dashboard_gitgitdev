#!/usr/bin/env python3
"""Serves dist/ on 127.0.0.1 for the Cloudflare tunnel (Python standard library only).

    python3 serve.py [--port 8796]

www.<domain> is redirected to the bare domain; unknown paths get dist/404.html.
Only GET/HEAD are served; every response carries strict security headers (CSP, HSTS, framing, permissions).
"""
import argparse
import functools
import os
import posixpath
import urllib.parse
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
ALLOWED_HOSTS = {"gitgitdev.my.id", "www.gitgitdev.my.id", "localhost", "127.0.0.1"}
DOMAIN = "gitgitdev.my.id"
# <sub>.gitgitdev.my.id -> product slug, from "subdomain" in each product.json (build.py writes dist/subdomains.json).
# On a product's subdomain its pages sit at the root (/, /privacy/, /terms/); the /<slug>/ paths on the main domain
# keep working, since app stores already link to them.
_subs = {"mtime": None, "map": {}}


def subdomains():
    f = os.path.join(DIST, "subdomains.json")
    try:
        m = os.path.getmtime(f)
        if m != _subs["mtime"]:
            import json
            with open(f) as fh:
                _subs.update(mtime=m, map=json.load(fh))
    except (OSError, ValueError):
        pass
    return _subs["map"]
SECURITY_HEADERS = {
    # The site is fully static: own styles and images only, no scripts, no forms, no frames.
    "Content-Security-Policy": "default-src 'none'; img-src 'self'; style-src 'self'; font-src 'self'; manifest-src 'self'; "
                               "base-uri 'none'; form-action 'none'; frame-ancestors 'none'; upgrade-insecure-requests",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), "
                          "payment=(), usb=(), interest-cohort=(), browsing-topics=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
    "X-Permitted-Cross-Domain-Policies": "none",
}


class Handler(SimpleHTTPRequestHandler):
    server_version = "gitgitdev"
    timeout = 20  # drop idle/slow connections
    sys_version = ""
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      ".txt": "text/plain; charset=utf-8", ".webp": "image/webp", ".svg": "image/svg+xml",
                      ".xml": "application/xml; charset=utf-8", ".html": "text/html; charset=utf-8"}

    def send_head(self):
        host = (self.headers.get("Host") or "").split(":")[0].lower()
        sub = host[:-len(DOMAIN) - 1] if host.endswith("." + DOMAIN) else ""
        slug = subdomains().get(sub)
        if host not in ALLOWED_HOSTS and not slug:
            return self.plain(HTTPStatus.MISDIRECTED_REQUEST, b"Unknown host")
        url_path = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path)
        if not url_path.startswith("/") or "\\" in url_path or "\x00" in url_path:
            return self.plain(HTTPStatus.BAD_REQUEST, b"Bad request")
        if slug and not url_path.startswith(("/static/", f"/{slug}/")) and url_path not in ("/favicon.ico", "/robots.txt"):
            # serve the product folder at the subdomain's root
            url_path = f"/{slug}" + url_path
            self.path = urllib.parse.quote(url_path, safe="/-._~")
        if host.startswith("www."):
            # Redirect only to our own domain, with a normalised path (no open redirect via //evil.example).
            target = "/" + posixpath.normpath(url_path).lstrip("/")
            if url_path.endswith("/") and not target.endswith("/"):
                target += "/"
            self.send_response(HTTPStatus.MOVED_PERMANENTLY)
            self.send_header("Location", "https://" + host[4:] + urllib.parse.quote(target, safe="/-._~"))
            self.send_header("Content-Length", "0")
            self.end_headers()
            return None
        # Hide dotfiles and dot-directories, except the public /.well-known/ folder.
        parts = [part for part in url_path.split("/") if part]
        if any(part.startswith(".") for part in parts) and not (parts[0] == ".well-known" and len(parts) == 2 and parts[1] != ".."):
            return self.not_found()
        path = self.translate_path(self.path)
        real = os.path.realpath(path)
        if not (real == DIST or real.startswith(DIST + os.sep)) or not os.path.exists(real):
            return self.not_found()
        return super().send_head()

    def plain(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        return None

    def method_not_allowed(self):
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self.send_header("Allow", "GET, HEAD")
        self.send_header("Content-Length", "0")
        self.end_headers()

    do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_TRACE = do_CONNECT = method_not_allowed

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
        # Pages always revalidate so a fix shows up at once; images and versioned CSS keep a day of cache.
        self.send_header("Cache-Control", "public, max-age=86400" if cacheable else "no-cache")
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        super().end_headers()

    def version_string(self):
        return self.server_version

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
