# Quadrix Radio — Deployment

Bu papka **production stack** uchun konfiguratsiyalarini saqlaydi:
Django boshqaruv paneli + DRF API, PostgreSQL, Redis, Celery, Icecast,
Liquidsoap, Nginx (TLS bilan), va Cloudflare CDN tavsiya etiladi.

## Arxitektura

```
Mobile app (driver)
        │  HTTPS
        ▼
    Cloudflare CDN
        │
        ▼
      Nginx (443)  ──▶  Django (admin + /api/*)        ──▶ PostgreSQL
        │             └▶ Celery worker / beat          ──▶ Redis
        │
        └▶ Icecast (/stream.mp3)  ◀── Liquidsoap   ◀── Playlist .m3u (Django yozadi)
                                              ◀── Live source (DJ harbor)
```

Django **hech qachon** mobile app uchun audio uzatmasin. Audio faqat
Icecast orqali ketadi. Django playlistlarni .m3u faylga yozadi va
Liquidsoap uni `reload_mode="watch"` bilan o'qiydi.

## 1. Birinchi marta o'rnatish

```bash
cp ../.env.example ../.env
# .env faylda SECRET_KEY, DB parolini, ICECAST_*, REDIS_* va boshqalarni
# to'ldiring. ICECAST_PUBLIC_BASE ni ichki manzilga (icecast:8000) qoldirib,
# tashqi mobile app uchun esa Nginx orqali https://radio.example.com/stream
# beriladi.

cd deploy
docker compose up -d --build
docker compose exec django python manage.py migrate
docker compose exec django python manage.py createsuperuser
```

## 2. Icecast parollarini almashtirish

`deploy/icecast.xml` ichida `change-me-*` joylarini almashtiring va
`docker-compose.yml` dagi env qiymatlari bilan moslang.
Liquidsoap `radio.liq` ham source-password ni biladi — uni ham yangilang.

## 3. SSL sertifikat

Birinchi marta:

```bash
docker compose run --rm --entrypoint "" \
    -v $(pwd)/certbot_www:/var/www/certbot \
    -v $(pwd)/certbot_etc:/etc/letsencrypt \
    certbot/certbot certonly --webroot -w /var/www/certbot \
    -d radio.example.com -m admin@example.com --agree-tos -n
docker compose exec nginx nginx -s reload
```

Avtomatik yangilash uchun cron yoki Watchtower-style sidecar qo'shing.

## 4. Liquidsoap playlist papkasi

Django Celery taski (`sync_playlist_to_liquidsoap`) `/srv/playlists/<slug>.m3u`
faylini yozadi, `<slug>` — RadioStation slug. `radio.liq` esa `main.m3u`
ni o'qiydi (default station). Ko'p kanal kerak bo'lsa `radio.liq` ga
har biri uchun `playlist(...)` + `output.icecast(...)` blokini qo'shing.

## 5. Mobile app endpoints

```
GET  /api/radio/stations/          — kanallar ro'yxati
GET  /api/radio/current/?station=  — hozirgi trek
GET  /api/radio/status/?station=   — online/listeners/bitrate
GET  /api/radio/playlist/today/    — bugungi playlist
GET  /api/radio/live/?station=     — jonli efir holati

POST /api/analytics/session/start/      — sessiya boshlash
POST /api/analytics/session/heartbeat/  — har 30 s
POST /api/analytics/session/end/        — sessiyani yopish
POST /api/analytics/event/              — track/ad/error log

POST /api/notifications/devices/register/
POST /api/notifications/devices/unregister/

POST /api/ads/next/                — keyingi adni so'rash
POST /api/ads/log/                 — ad eshitilgani uchun log
```

Audio fayl URL: `https://radio.example.com/stream.mp3` (Icecast).

## 6. Push notifications (FCM)

Firebase service-account JSON ni serverga yuklang va `.env` da yo'lni
kiriting:

```
FCM_PROJECT_ID=quadrix-radio-prod
FCM_SERVICE_ACCOUNT_FILE=/run/secrets/fcm.json
```

Adminda **Notifications → Push campaigns → action "Queue selected"** orqali
jo'natiladi.

## 7. Monitoring

- `/admin/` — Unfold dashboard (RadioStation list, listeners, online badge).
- `/silk/` — DEBUG da request/SQL profiling.
- `flower -A config` — Celery monitoring (`celery -A config flower --port=5555`).
- Icecast `/admin/stats.xsl` — listener statistikasi (admin paroli).
- `radio.tasks.health.check_radio_health` har minutda Icecast ni tekshiradi
  va RadioStation.online ni yangilaydi.

## 8. CDN (Cloudflare)

`radio.example.com` ni Cloudflare orqali o'tkazing. **MUHIM**: Icecast stream
uchun "Cache Everything" rule qo'ymang — audio live, cache qilinmasin.
Faqat `/static/` va `/media/` ni cache qilish foydali. API javoblari
qisqa TTL bilan Nginx tomonidan cache qilinadi.

## 9. Skalalash

Foydalanuvchilar 5–10K dan oshsa:
- Icecast relay node'lar qo'shing (`<relay>` Icecast XML da).
- Django `gunicorn --workers 8 --threads 4` va alohida read-only replikalar.
- PostgreSQL connection pool: PgBouncer.
- Cloudflare/CloudFront CDN ListenerLog yozuvlarini tashlasin.
