from django.conf.urls import url

from . import views

app_name = 'django_lightweight_queue'

urlpatterns = (
    url(r'^debug/django-lightweight-queue/debug-run$', views.debug_run, name='debug-run'),
)
