import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Sozlamalarni Django settings'dan o'qiymiz, hammasi `CELERY_` prefiksi bilan.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Har bir ilovaning `tasks.py` faylini avtomatik topish.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Celery ishlayotganini tekshirish uchun oddiy task."""
    print(f'Request: {self.request!r}')
