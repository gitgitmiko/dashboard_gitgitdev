#!/usr/bin/env python3
"""Creates products/<slug>/ for a new app or game.

    python3 new_product.py <slug> "<Nama Produk>" [game|app]

The new product starts with "hidden": true so it stays off the site until its texts and images are filled in.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    slug, name = sys.argv[1], sys.argv[2]
    kind = sys.argv[3] if len(sys.argv) > 3 else "app"
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        sys.exit("slug hanya huruf kecil, angka, dan tanda minus (contoh: dumpling-witch)")
    if kind not in ("game", "app"):
        sys.exit("jenis harus game atau app")
    folder = os.path.join(ROOT, "products", slug)
    if os.path.exists(folder):
        sys.exit(f"{folder} sudah ada")
    os.makedirs(os.path.join(folder, "assets", "screenshots"))
    package = "com.gitgitmiko." + slug.replace("-", "")
    product = {
        "name": name,
        "kind": kind,
        "order": 100,
        "hidden": True,
        "status": "coming_soon",
        "package": package,
        "play_url": "",
        "tagline": "Satu kalimat tentang " + name + ".",
        "genre": "",
        "platform": "Android",
        "accent": "#7c5cff",
        "accent_2": "#ff78b0",
        "description": ["Paragraf deskripsi."],
        "features": [["Fitur", "Penjelasan singkat."]],
        "screenshots": [["01.webp", "Keterangan screenshot"]],
        "privacy": {
            "effective": "",
            "account": False,
            "local_save": "Data aplikasi",
            "local_save_en": "App data",
            "ads_admob": False,
            "ads_moment": "",
            "ads_moment_en": "",
            "min_age": 13,
        },
    }
    with open(os.path.join(folder, "product.json"), "w", encoding="utf-8") as handle:
        json.dump(product, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"Dibuat: products/{slug}/product.json")
    print("Isi teksnya, taruh assets/icon.png (512x512), assets/feature.webp (1024x500) dan screenshots/*.webp,")
    print('hapus "hidden": true, lalu jalankan: python3 build.py')


if __name__ == "__main__":
    main()
