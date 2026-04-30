# Django Base — Yangi Boshlovchilar uchun Boilerplate

Bu loyiha Django'da yangi proyekt boshlash uchun tayyor shablon. Ichida quyidagilar oldindan sozlangan:

- **Django 5.1** — asosiy framework
- **Django REST Framework** — API yozish uchun
- **drf-yasg** — Swagger/Redoc API hujjatlari
- **django-unfold** — chiroyli admin panel
- **django-cors-headers** — CORS sozlamalari
- **django-silk** — so'rovlarni profiling qilish (debug uchun)
- **python-decouple** — `.env` fayldan sozlamalarni o'qish
- **PostgreSQL** yoki **SQLite** — istalganini tanlash mumkin
- **Celery + Redis** — fon (background) tasklar uchun
- **django-celery-beat** — periodik tasklar (cron) uchun
- **flower** — Celery monitoring dashboard'i

---

## 📁 Loyiha tuzilishi

```
django_base/
├── config/                  # Loyiha asosiy sozlamalari
│   ├── settings.py          # .env'dan o'qiydigan asosiy settings
│   ├── custom_config.py     # Unfold, logging, swagger sozlamalari
│   ├── celery.py            # Celery application instance
│   ├── urls.py              # Asosiy URL marshrutlari
│   ├── wsgi.py / asgi.py    # Server entrypoints
│   └── __init__.py          # celery_app import qiladi
├── main/                    # Birinchi (asosiy) ilova
│   ├── models/              # Modellar (papka shaklida)
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── health.py        # HealthCheck modeli (misol)
│   ├── admin.py             # Admin panel sozlamalari
│   ├── apps.py
│   ├── serializers.py       # DRF serializerlar
│   ├── tasks.py             # Celery tasklar yoziladigan joy
│   ├── views.py             # API view'lar
│   └── urls.py              # /health/, /health-checks/ va b.
├── manage.py
├── requirements.txt
├── .env.example             # Namuna .env (git'ga yuklanadi)
├── .env                     # Sizning shaxsiy sozlamalaringiz (git'ga yuklanmaydi)
├── .gitignore
└── README.md
```

---

## 🚀 Ishga tushirish (Quick Start)

### 1. Loyihani clone qiling

```bash
git clone <repository-url>
cd django_base
```

### 2. Virtual environment yarating va faollashtiring

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Kerakli paketlarni o'rnating

```bash
pip install -r requirements.txt
```

### 4. `.env` faylini yarating

```bash
cp .env.example .env
```

So'ng `.env` faylini ochib, qiymatlarni o'zgartiring (ayniqsa `SECRET_KEY` ni).

Yangi `SECRET_KEY` yaratish uchun:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 5. Migratsiyalarni ishga tushiring

```bash
python manage.py migrate
```

### 6. Superuser (admin) yarating

```bash
python manage.py createsuperuser
```

### 7. Serverni ishga tushiring

```bash
python manage.py runserver
```

Endi quyidagilarni brauzerda ochishingiz mumkin:

- 🏠 Asosiy: http://127.0.0.1:8000/
- 🔧 Admin: http://127.0.0.1:8000/admin/
- 📘 Swagger: http://127.0.0.1:8000/api/swagger/
- 📗 Redoc: http://127.0.0.1:8000/api/redoc/
- 🔍 Silk (profiler): http://127.0.0.1:8000/silk/

---

## ⚙️ `.env` sozlamalari

| O'zgaruvchi | Tavsif | Default |
|---|---|---|
| `SECRET_KEY` | Django maxfiy kaliti | — |
| `DEBUG` | Debug rejimi (True/False) | `True` |
| `ALLOWED_HOSTS` | Ruxsat etilgan hostlar (vergul bilan) | `*` |
| `USE_POSTGRES` | True — PostgreSQL, False — SQLite | `False` |
| `DB_NAME` | PostgreSQL ma'lumotlar bazasi nomi | — |
| `DB_USER` | PostgreSQL foydalanuvchi | — |
| `DB_PASSWORD` | PostgreSQL paroli | — |
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `ENABLE_SILK` | django-silk yoqilsinmi | `True` |
| `LOGGING_STATUS` | Loglarni faylga yozish | `True` |
| `CORS_ALLOW_ALL_ORIGINS` | Hamma origin'larga ruxsat | `True` |
| `CORS_ALLOWED_ORIGINS` | Aniq origin'lar (vergul bilan) | — |
| `SITE_TITLE` | Admin panel sarlavhasi | `Django Base` |
| `SITE_HEADER` | Admin panel header'i | `Django Base Admin` |
| `LANGUAGE_CODE` | Til kodi | `en-us` |
| `TIME_ZONE` | Vaqt zonasi | `UTC` |
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_DB` | Redis DB raqami | `0` |
| `REDIS_PASSWORD` | Redis paroli (bo'lmasa bo'sh) | — |
| `CELERY_BROKER_URL` | Aniq broker URL (bo'sh bo'lsa REDIS_*'dan tuziladi) | — |
| `CELERY_RESULT_BACKEND` | Natija backend (bo'sh bo'lsa `django-db`) | `django-db` |
| `CELERY_TASK_ALWAYS_EAGER` | True — task'lar darhol bajariladi (worker kerak emas) | `False` |

---

## 🐘 PostgreSQL ga o'tish

1. PostgreSQL'ni o'rnating va ma'lumotlar bazasi yarating:
   ```sql
   CREATE DATABASE django_base;
   CREATE USER myuser WITH PASSWORD 'mypassword';
   GRANT ALL PRIVILEGES ON DATABASE django_base TO myuser;
   ```

2. `.env` faylini yangilang:
   ```env
   USE_POSTGRES=True
   DB_NAME=django_base
   DB_USER=myuser
   DB_PASSWORD=mypassword
   DB_HOST=localhost
   DB_PORT=5432
   ```

3. Migratsiyalarni qayta ishga tushiring:
   ```bash
   python manage.py migrate
   ```

---

## ⚡ Celery va Redis bilan ishlash

### 1. Redis serverni ishga tushirish

**Docker bilan (eng oson):**
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt install redis-server
sudo systemctl start redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

Tekshirish:
```bash
redis-cli ping   # → PONG
```

### 2. Celery worker'ni ishga tushirish

**Yangi terminalda** (venv faollashgan holda):
```bash
celery -A config worker -l info
```

### 3. (Ixtiyoriy) Celery Beat — periodik tasklar

```bash
celery -A config beat -l info
```

Periodik tasklarni Django admin'dan boshqarasiz: http://127.0.0.1:8000/admin/django_celery_beat/

### 4. (Ixtiyoriy) Flower — monitoring UI

```bash
celery -A config flower
```
So'ng oching: http://127.0.0.1:5555/

### 5. Yangi task yozish

[main/tasks.py](main/tasks.py) faylida yozing:

```python
from celery import shared_task

@shared_task
def send_email(user_id, subject, body):
    # ... emailni yuborish kodi
    return 'sent'
```

Chaqirish:
```python
from main.tasks import send_email

send_email.delay(user.id, "Salom", "Test xabar")               # asinxron
send_email.apply_async((user.id, "Salom", "..."), countdown=60)  # 60 sekunddan keyin
```

### 6. Redis kerak bo'lmagan rejim (development uchun)

`.env` da:
```env
CELERY_TASK_ALWAYS_EAGER=True
```

Bu rejimda `task.delay()` chaqirilganda task darhol shu joyda bajariladi — Redis ham, worker ham kerak emas.

---

## 🩺 Health Check API (misol)

Loyiha ichida tayyor misol API'lar bor — yangi endpoint yozish uchun shablon sifatida ishlatishingiz mumkin.

| Method | URL | Tavsif |
|---|---|---|
| GET | `/api/v1/health/` | DB, Redis, Celery holatini real vaqtda ko'rsatadi |
| POST | `/api/v1/health/trigger/` | Celery task ishga tushiradi (natijani DB ga yozadi) |
| GET | `/api/v1/health-checks/` | Saqlangan health check natijalari ro'yxati |
| GET | `/api/v1/health-checks/{id}/` | Bitta natija tafsiloti |

Sinash:
```bash
curl http://127.0.0.1:8000/api/v1/health/
curl -X POST http://127.0.0.1:8000/api/v1/health/trigger/
```

---

## 📦 Yangi ilova (app) qo'shish

```bash
python manage.py startapp myapp
```

So'ng [config/settings.py](config/settings.py#L62) faylida `CUSTOM_APPS` ro'yxatiga qo'shing:

```python
CUSTOM_APPS = [
    'main',
    'myapp',
]
```

---

## 🛠 Foydali buyruqlar

```bash
# Migratsiya yaratish
python manage.py makemigrations

# Migratsiyani qo'llash
python manage.py migrate

# Statik fayllarni yig'ish (production)
python manage.py collectstatic

# Django shell
python manage.py shell

# Test ishga tushirish
python manage.py test
```

---

## 🔒 Production'ga deploy qilishdan oldin

Quyidagilarni `.env` da albatta o'zgartiring:

```env
DEBUG=False
SECRET_KEY=<yangi-uzun-tasodifiy-kalit>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
USE_POSTGRES=True
ENABLE_SILK=False
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://yourdomain.com
```

So'ngra:
```bash
python manage.py collectstatic --noinput
python manage.py migrate
```

---

## ❓ Tez-tez beriladigan savollar

**S: `.env` fayli yo'q, xato beryapti.**
J: `.env.example` ni nusxa olib `.env` deb nomlang: `cp .env.example .env`

**S: PostgreSQL bilan xatolik beryapti (`psycopg2` topilmadi).**
J: `pip install -r requirements.txt` ni qayta ishga tushiring. Linux'da `sudo apt install libpq-dev` kerak bo'lishi mumkin.

**S: Migration xatolar beryapti.**
J: `db.sqlite3` faylini o'chirib, qaytadan `python manage.py migrate` qiling.

---

## 📝 Litsenziya

MIT
