from django.urls import re_path

from . import views

app_name = 'django_lightweight_queue'

urlpatterns = (
    re_path(r'^debug/django-lightweight-queue/debug-run$', views.debug_run, name='debug-run'),
)
