from django.urls import path

from . import views

app_name = 'django_lightweight_queue'

urlpatterns = (
    path(r'debug/django-lightweight-queue/debug-run', views.debug_run, name='debug-run'),
)
