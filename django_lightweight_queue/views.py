import io
import json
import logging

from django import template
from django.db import transaction
from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse

from .job import Job
from .types import QueueName, WorkerNumber


# Note: no authentication here -- ensure you only connect up this view in
# development!
def debug_run(request: HttpRequest) -> HttpResponse:
    """
    Run a task on a `GET` request and within a transaction which will always be
    rolled back.

    This is useful for debugging tasks and for optimising their database
    accesses (via the Django Debug Toolbar).

    Logging output from the task is captured and included on the page, though
    `print` calls are not.

    You should take care when using this to debug tasks which interact with
    services other than the database (e.g: caches or HTTP endpoints), as *only*
    the database transaction is rolled back after the task completes. Any other
    external requests will happen as normal.

    To make this view available you'll need to have your main Django project
    include its url somewhere. You are *strongly* encouraged only to do this in
    DEBUG mode:
    ```
    if settings.DEBUG:
        urlpatterns += (
            url(r'', include('django_lightweight_queue.urls', namespace='django-lightweight-queue')),
        )
    ```
    """

    if not settings.DEBUG:
        raise Http404("Debug view only available when DEBUG=True")

    job = Job.from_json(request.GET['job'])

    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)

    try:
        logging.root.addHandler(handler)
        with transaction.atomic():
            result = job.run(queue=QueueName('debug'), worker_num=WorkerNumber(0))
            transaction.set_rollback(rollback=True)
    finally:
        logging.root.removeHandler(handler)

    document = template.Template("""
    <!doctype html>
    <html>
        <head>
            <title>Debug Run {{ path }}</title>
        </head>
        <body>
            <h2>Debug Run {{ path }}</h2>
            <p><strong>Result:</strong> {{ result }}</p>
            <code><pre>{{ job }}</pre></code>
            <code><pre>{{ log }}</pre></code>
        </body>
    </html>
    """).render(template.Context({
        'path': job.path,
        'job': json.dumps(job.as_dict(), sort_keys=True, indent=4),
        'result': result,
        'log': log_stream.getvalue(),
    }))

    return HttpResponse(document.encode('utf-8'))
