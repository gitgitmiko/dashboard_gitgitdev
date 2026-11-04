# GitgitDev — situs developer

Situs statis untuk https://gitgitdev.my.id: halaman depan berisi daftar produk, halaman tiap app/game, kebijakan privasi per produk, dan `app-ads.txt` untuk AdMob. Dipakai sebagai *Website* dan *Privacy policy* di Play Console.

Tanpa dependensi: cukup Python 3 standar.

## Struktur

```
site.json                     nama studio, email kontak, baris app-ads.txt, warna
products/<slug>/product.json  data satu produk (teks, fitur, screenshot, status, privasi)
products/<slug>/assets/       icon.png (512), feature.webp (1024x500), screenshots/*.webp
static/                       style.css, logo (logo-mark.png, logo-full.webp), favicon, og-image.jpg
brand/                        logo asli resolusi penuh (tidak ikut dipublikasikan)
build.py                      membuat dist/ dari data di atas
serve.py                      server statis 127.0.0.1:8796 (www -> domain utama, halaman 404)
new_product.py                membuat folder produk baru
deploy/gitgitdev-site.service unit systemd --user
```

URL yang dihasilkan:

| URL | Isi |
|---|---|
| `/` | beranda + kartu semua produk |
| `/<slug>/` | halaman produk (feature graphic, fitur, screenshot, tombol Google Play) |
| `/<slug>/privacy/` | kebijakan privasi produk (ID + EN), dibuat dari blok `privacy` |
| `/<slug>/<nama>/` | halaman tulisan tangan dari `products/<slug>/pages/<nama>.html` (mis. `hapus-akun`) |
| `/privacy/` | daftar kebijakan privasi |
| `/app-ads.txt` | dari `site.json` → `app_ads_txt` |
| `/robots.txt`, `/sitemap.xml`, `/404.html`, `/.well-known/security.txt` | otomatis |

## Menambah app/game baru

```bash
python3 new_product.py nama-app "Nama App" game   # atau app
# isi products/nama-app/product.json, taruh gambar di assets/, hapus "hidden": true
python3 build.py
```

Gambar sebaiknya WebP (screenshot ±80% kualitas). Screenshot HP (portrait, 720×1280): tambahkan `"screenshot_orientation": "portrait"` di product.json. Ikon tetap PNG 512×512 (sama dengan ikon Play Store).

Saat app sudah tayang: isi `"play_url"` dengan link Play Store dan ubah `"status"` ke `"live"` (pilihan lain: `"coming_soon"`, `"testing"`). Kalau app memakai AdMob dengan akun yang sama, `app-ads.txt` tidak perlu diubah; untuk jaringan iklan lain tambahkan barisnya di `site.json`.

Field `privacy`:
- `account`: `true` kalau app punya akun pengguna (Play juga mewajibkan halaman hapus akun).
- `ads_admob`: `true` menambah bagian iklan Google AdMob; `ads_moment` menjelaskan kapan iklan muncul.
- `local_save`: data apa yang disimpan di perangkat.
- `min_age`: usia minimum target pengguna.

Kalau app mengumpulkan data lain (login, analitik, pembelian), tulis kebijakannya secara khusus — jangan andalkan templat: buat `products/<slug>/pages/privacy.html`, yang menggantikan kebijakan dari templat (contoh: `products/valoid/`).

Halaman di `pages/` berupa potongan HTML; baris pertamanya `<!-- title: Judul -->`, dan `{{contact_email}}` diganti email kontak. Selain `privacy`, setiap halaman juga ditautkan dari halaman produk.

## Menjalankan

Layanan berjalan sebagai `systemd --user` dan membangun ulang situs setiap start:

```bash
cp deploy/gitgitdev-site.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now gitgitdev-site
systemctl --user restart gitgitdev-site   # setelah mengubah konten
```

Tunnel Cloudflare (`~/.cloudflared/config.yml`, layanan `cloudflared-webunime`) meneruskan `gitgitdev.my.id` dan `www.gitgitdev.my.id` ke `http://127.0.0.1:8796`. DNS di Cloudflare: CNAME `@` dan `www` → `<id-tunnel>.cfargotunnel.com` (proxied).

Uji lokal: `python3 build.py && python3 serve.py` lalu buka http://127.0.0.1:8796.

## Keamanan

`serve.py` hanya melayani GET/HEAD untuk host `gitgitdev.my.id` (+ `www`, yang dialihkan), menyembunyikan dotfile kecuali `/.well-known/`, dan mengirim header CSP ketat (tanpa skrip, tanpa inline style, tanpa iframe), HSTS, `X-Frame-Options`, `Permissions-Policy`, dan COOP/CORP.

Karena CSP melarang inline style, jangan pakai `style="..."`, `<style>`, atau `<script>` di `pages/*.html`. Warna produk (`accent`, `accent_2`, wajib `#rrggbb`) dibuat oleh `build.py` menjadi `static/theme.css` sebagai kelas `.theme-<slug>`.
