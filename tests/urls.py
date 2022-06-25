from django.urls import path, include

urlpatterns = [
    path('', include('django_lightweight_queue.urls', namespace='django-lightweight-queue')),
]
