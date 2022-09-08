from django_lightweight_queue.types import QueueName

LIGHTWEIGHT_QUEUE_BACKEND_OVERRIDES = {
    QueueName('test-queue'): 'tests.test_extra_settings.TestBackend',
}

LIGHTWEIGHT_QUEUE_REDIS_PASSWORD = 'a very bad password'
