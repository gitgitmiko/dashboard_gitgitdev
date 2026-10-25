#!/usr/bin/env python3
"""Builds the GitgitDev developer site into dist/ (Python standard library only).

    python3 build.py

Inputs:  site.json, products/<slug>/product.json (+ assets/, pages/), static/
Outputs: dist/index.html, dist/<slug>/index.html, dist/<slug>/privacy/index.html, dist/<slug>/<page>/index.html,
         dist/privacy/index.html, dist/app-ads.txt, dist/robots.txt, dist/sitemap.xml, dist/404.html
"""
import datetime
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
KIND_LABEL = {"game": "Game", "app": "Aplikasi"}
STATUS_LABEL = {"live": "Tersedia di Google Play", "coming_soon": "Segera di Google Play", "testing": "Uji coba tertutup"}


def esc(value):
    return html.escape(str(value), quote=True)


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def load_products():
    products = []
    folder = os.path.join(ROOT, "products")
    for slug in sorted(os.listdir(folder)):
        path = os.path.join(folder, slug, "product.json")
        if not os.path.isfile(path):
            continue
        product = load_json(path)
        product["slug"] = slug
        for key in ("name", "kind", "status", "tagline"):
            if not product.get(key):
                sys.exit(f"products/{slug}/product.json: '{key}' wajib diisi")
        if product.get("hidden"):
            continue
        products.append(product)
    products.sort(key=lambda p: (p.get("order", 999), p["name"]))
    return products


def page(site, title, description, body, path, accent=None, accent_2=None, image=None):
    accent = accent or site["accent"]
    accent_2 = accent_2 or site["accent_2"]
    url = site["base_url"].rstrip("/") + path
    og_image = f'<meta property="og:image" content="{esc(site["base_url"].rstrip("/") + image)}">' if image else ""
    year = datetime.date.today().year
    return f"""<!doctype html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:type" content="website">
{og_image}
<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/static/style.css">
<style>:root {{ --accent: {esc(accent)}; --accent-2: {esc(accent_2)}; }}</style>
</head>
<body>
<header class="top">
  <a class="brand" href="/"><span class="logo" aria-hidden="true"></span>{esc(site["name"])}</a>
  <nav><a href="/#produk">Produk</a><a href="/privacy/">Privasi</a><a href="mailto:{esc(site["contact_email"])}">Kontak</a></nav>
</header>
<main>
{body}
</main>
<footer class="foot">
  <p>&copy; {year} {esc(site["name"])} &middot; {esc(site["developer"])} &middot; <a href="mailto:{esc(site["contact_email"])}">{esc(site["contact_email"])}</a></p>
  <p class="small">Google Play dan logo Google Play adalah merek dagang Google LLC.</p>
</footer>
</body>
</html>
"""


def play_button(product):
    label = STATUS_LABEL.get(product["status"], STATUS_LABEL["coming_soon"])
    if product.get("play_url") and product["status"] == "live":
        return f'<a class="btn play" href="{esc(product["play_url"])}" rel="noopener">{play_icon()}<span>{esc(label)}</span></a>'
    return f'<span class="btn play disabled">{play_icon()}<span>{esc(label)}</span></span>'


def play_icon():
    return ('<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">'
            '<path fill="currentColor" d="M4 2.8v18.4c0 .7.8 1.1 1.4.7l15.4-9.2c.6-.3.6-1.1 0-1.4L5.4 2.1C4.8 1.7 4 2.1 4 2.8z"/></svg>')


def asset(product, name):
    return f"/{product['slug']}/assets/{name}"


def home(site, products):
    cards = []
    for p in products:
        icon = asset(p, "icon.png") if os.path.isfile(os.path.join(ROOT, "products", p["slug"], "assets", "icon.png")) else "/static/favicon.svg"
        cards.append(f"""
  <a class="card" href="/{esc(p["slug"])}/" style="--accent:{esc(p.get("accent", site["accent"]))};--accent-2:{esc(p.get("accent_2", site["accent_2"]))}">
    <img class="icon" src="{esc(icon)}" alt="" width="96" height="96" loading="lazy">
    <div>
      <p class="kicker">{esc(KIND_LABEL.get(p["kind"], p["kind"]))} &middot; {esc(STATUS_LABEL.get(p["status"], ""))}</p>
      <h3>{esc(p["name"])}</h3>
      <p>{esc(p["tagline"])}</p>
    </div>
  </a>""")
    body = f"""
<section class="hero">
  <h1>{esc(site["tagline"])}</h1>
  <p class="lead">{esc(site["intro"])}</p>
  <a class="btn" href="#produk">Lihat produk</a>
</section>
<section id="produk" class="section">
  <h2>Produk</h2>
  <div class="cards">{''.join(cards)}
  </div>
</section>
<section class="section narrow">
  <h2>Kontak</h2>
  <p>Pertanyaan, laporan bug, atau kerja sama: <a href="mailto:{esc(site["contact_email"])}">{esc(site["contact_email"])}</a>.</p>
</section>"""
    return page(site, f'{site["name"]} — {site["tagline"]}', site["intro"], body, "/")


def load_pages(site, p):
    """Hand-written pages from products/<slug>/pages/<name>.html, served at /<slug>/<name>/.

    Each file is an HTML fragment whose first line is <!-- title: ... -->; {{contact_email}} is replaced.
    A pages/privacy.html replaces the generated privacy policy.
    """
    folder = os.path.join(ROOT, "products", p["slug"], "pages")
    pages = []
    if not os.path.isdir(folder):
        return pages
    for filename in sorted(os.listdir(folder)):
        name, ext = os.path.splitext(filename)
        if ext != ".html":
            continue
        with open(os.path.join(folder, filename), encoding="utf-8") as handle:
            text = handle.read()
        match = re.match(r"\s*<!--\s*title:\s*(.*?)\s*-->", text)
        if not match:
            sys.exit(f"products/{p['slug']}/pages/{filename}: baris pertama harus <!-- title: ... -->")
        pages.append((name, match.group(1), text[match.end():].replace("{{contact_email}}", esc(site["contact_email"]))))
    return pages


def custom_page(site, p, name, title, body):
    return page(site, f'{title} — {p["name"]}', f'{title} {p["name"]}.', f'<article class="section narrow legal">{body}</article>',
                f'/{p["slug"]}/{name}/', p.get("accent"), p.get("accent_2"))


def product_page(site, p, pages=()):
    shots = "".join(
        f'<figure><img src="{esc(asset(p, "screenshots/" + name))}" alt="{esc(caption)}" loading="lazy" width="1280" height="720"><figcaption>{esc(caption)}</figcaption></figure>'
        for name, caption in p.get("screenshots", []))
    features = "".join(f"<li><strong>{esc(title)}</strong><span>{esc(text)}</span></li>" for title, text in p.get("features", []))
    description = "".join(f"<p>{esc(text)}</p>" for text in p.get("description", []))
    feature_img = ""
    if os.path.isfile(os.path.join(ROOT, "products", p["slug"], "assets", "feature.webp")):
        feature_img = f'<img class="feature" src="{esc(asset(p, "feature.webp"))}" alt="{esc(p["name"])}" width="1024" height="500">'
    extra_links = "".join(f'<a class="btn ghost" href="/{esc(p["slug"])}/{esc(name)}/">{esc(title)}</a>'
                          for name, title, _ in pages if name != "privacy")
    shots_html = f'''
<section class="section">
  <h2>Tangkapan layar</h2>
  <div class="shots">{shots}</div>
</section>''' if shots else ""
    facts = [("Jenis", p.get("genre", KIND_LABEL.get(p["kind"], ""))), ("Platform", p.get("platform", "Android")), ("Paket", p.get("package", ""))]
    facts_html = "".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in facts if v)
    body = f"""
<section class="product-hero">
  {feature_img}
  <div class="product-head">
    <img class="icon big" src="{esc(asset(p, "icon.png"))}" alt="" width="128" height="128">
    <div>
      <p class="kicker">{esc(KIND_LABEL.get(p["kind"], p["kind"]))}</p>
      <h1>{esc(p["name"])}</h1>
      <p class="lead">{esc(p["tagline"])}</p>
      <div class="actions">{play_button(p)}<a class="btn ghost" href="/{esc(p["slug"])}/privacy/">Kebijakan privasi</a>{extra_links}</div>
    </div>
  </div>
</section>
<section class="section narrow">{description}</section>
<section class="section">
  <h2>Fitur</h2>
  <ul class="features">{features}</ul>
</section>
{shots_html}
<section class="section narrow">
  <dl class="facts">{facts_html}</dl>
  <p>Bantuan dan laporan bug: <a href="mailto:{esc(site["contact_email"])}?subject={esc(p["name"])}">{esc(site["contact_email"])}</a></p>
</section>"""
    image = asset(p, "feature.webp") if feature_img else None
    return page(site, f'{p["name"]} — {site["name"]}', p["tagline"], body, f'/{p["slug"]}/',
                p.get("accent"), p.get("accent_2"), image)


def privacy_page(site, p):
    pv = p.get("privacy", {})
    name = esc(p["name"])
    email = esc(site["contact_email"])
    dev = esc(site["developer"])
    ads_id = ads_en = ""
    if pv.get("ads_admob"):
        moment = pv.get("ads_moment", "di dalam aplikasi")
        moment_en = pv.get("ads_moment_en", "inside the app")
        ads_id = f"""<h2>Iklan</h2>
<p>{name} menampilkan iklan dari Google AdMob, misalnya {moment}. Google dapat mengumpulkan dan memproses data seperti ID iklan perangkat, alamat IP, informasi perangkat, dan interaksi dengan iklan untuk menampilkan iklan, mengukur performa, dan mencegah penipuan. Pengolahan tersebut tunduk pada <a href="https://policies.google.com/privacy">Kebijakan Privasi Google</a> dan <a href="https://policies.google.com/technologies/partner-sites">cara Google memakai data dari aplikasi mitra</a>. Anda dapat mereset atau menghapus ID iklan, atau memilih tidak menerima iklan yang dipersonalisasi, melalui Setelan &gt; Privasi &gt; Iklan di perangkat Android. Pengguna di wilayah yang mewajibkannya (misalnya EEA dan Inggris) diminta persetujuan sebelum iklan yang dipersonalisasi ditampilkan.</p>"""
        ads_en = f"""<p><strong>Ads.</strong> {name} shows ads from Google AdMob, for example {moment_en}. Google may collect and process data such as the device advertising ID, IP address, device information and ad interactions to serve ads, measure performance and prevent fraud, under the <a href="https://policies.google.com/privacy">Google Privacy Policy</a> and <a href="https://policies.google.com/technologies/partner-sites">how Google uses information from partner apps</a>. You can reset or delete your advertising ID, or opt out of personalised ads, in Settings &gt; Privacy &gt; Ads on your Android device. Users in regions that require it (such as the EEA and UK) are asked for consent before personalised ads are shown.</p>"""
    local = esc(pv.get("local_save", "Data aplikasi"))
    local_en = esc(pv.get("local_save_en", "App data"))
    account_id = "tidak meminta akun, " if not pv.get("account") else ""
    account_en = "requires no account, " if not pv.get("account") else ""
    age = int(pv.get("min_age", 13))
    body = f"""
<article class="section narrow legal">
<h1>Kebijakan Privasi {name}</h1>
<p>Berlaku sejak {esc(pv.get("effective", ""))}. Pengembang: {dev} ({esc(site["name"])}). Kontak: <a href="mailto:{email}">{email}</a>.</p>
<h2>Data yang kami kumpulkan</h2>
<p>{name} {account_id}tidak meminta izin lokasi, kamera, mikrofon, kontak, atau penyimpanan, dan tidak mengirim data pribadi ke server kami. {local} hanya disimpan di perangkat Anda dan terhapus jika aplikasi dihapus.</p>
{ads_id}
<h2>Anak-anak</h2>
<p>{name} ditujukan untuk pengguna berusia {age} tahun ke atas. Kami tidak dengan sengaja mengumpulkan data pribadi anak-anak.</p>
<h2>Perubahan</h2>
<p>Kebijakan ini dapat diperbarui. Versi terbaru selalu tersedia di halaman ini.</p>
<div class="en">
<h1>{name} Privacy Policy (English)</h1>
<p>Effective {esc(pv.get("effective", ""))}. Developer: {dev} ({esc(site["name"])}). Contact: <a href="mailto:{email}">{email}</a>.</p>
<p><strong>Data we collect.</strong> {name} {account_en}asks for no location, camera, microphone, contacts or storage permission, and sends no personal data to our servers. {local_en} is stored only on your device and is removed when the app is uninstalled.</p>
{ads_en}
<p><strong>Children.</strong> {name} is intended for users aged {age} and over. We do not knowingly collect personal data from children.</p>
<p><strong>Changes.</strong> This policy may be updated; the latest version is always on this page.</p>
</div>
</article>"""
    return page(site, f'Kebijakan Privasi — {p["name"]}', f'Kebijakan privasi {p["name"]}.', body,
                f'/{p["slug"]}/privacy/', p.get("accent"), p.get("accent_2"))


def privacy_index(site, products):
    items = "".join(f'<li><a href="/{esc(p["slug"])}/privacy/">{esc(p["name"])}</a></li>' for p in products)
    body = f"""
<article class="section narrow legal">
<h1>Privasi</h1>
<p>Setiap produk {esc(site["name"])} punya kebijakan privasinya sendiri:</p>
<ul>{items}</ul>
<p>Situs ini tidak memakai cookie pelacak atau analitik. Pertanyaan: <a href="mailto:{esc(site["contact_email"])}">{esc(site["contact_email"])}</a>.</p>
</article>"""
    return page(site, f'Privasi — {site["name"]}', "Kebijakan privasi produk GitgitDev.", body, "/privacy/")


def not_found(site):
    body = """
<section class="hero"><h1>Halaman tidak ditemukan</h1><p class="lead">Alamat ini tidak ada.</p><a class="btn" href="/">Ke beranda</a></section>"""
    return page(site, f'404 — {site["name"]}', "Halaman tidak ditemukan.", body, "/404.html")


def write(path, text):
    full = os.path.join(DIST, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as handle:
        handle.write(text)


def main():
    site = load_json(os.path.join(ROOT, "site.json"))
    products = load_products()
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    shutil.copytree(os.path.join(ROOT, "static"), os.path.join(DIST, "static"))
    write("index.html", home(site, products))
    write("privacy/index.html", privacy_index(site, products))
    write("404.html", not_found(site))
    urls = ["/", "/privacy/"]
    for p in products:
        assets = os.path.join(ROOT, "products", p["slug"], "assets")
        if os.path.isdir(assets):
            shutil.copytree(assets, os.path.join(DIST, p["slug"], "assets"))
        pages = load_pages(site, p)
        write(f'{p["slug"]}/index.html', product_page(site, p, pages))
        urls.append(f'/{p["slug"]}/')
        if not any(name == "privacy" for name, _, _ in pages):
            write(f'{p["slug"]}/privacy/index.html', privacy_page(site, p))
            urls.append(f'/{p["slug"]}/privacy/')
        for name, title, body in pages:
            write(f'{p["slug"]}/{name}/index.html', custom_page(site, p, name, title, body))
            urls.append(f'/{p["slug"]}/{name}/')
    write("app-ads.txt", "\n".join(site.get("app_ads_txt", [])) + "\n")
    base = site["base_url"].rstrip("/")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "".join(f"  <url><loc>{base}{u}</loc></url>\n" for u in urls) + "</urlset>\n")
    print(f"SITE_BUILD_OK {len(products)} produk -> {DIST}")


if __name__ == "__main__":
    main()
