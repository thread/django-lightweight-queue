import json
import threading

from socket import gethostname

try:
    from http.server import HTTPServer
except ImportError:
    from BaseHTTPServer import HTTPServer

from prometheus_client.exposition import MetricsHandler

from . import app_settings


def get_config_response(worker_queue_and_counts):
    """
    This is designed to be used by Prometheus, to direct it to scrape the
    correct ports and assign the correct labels to pull in data from all the
    running queue workers.
    """
    return [
        {
            "targets": [
                "%s:%d" % (
                    gethostname(),
                    app_settings.PROMETHEUS_START_PORT + index,
                ),
            ],
            "labels": {
                "django_lightweight_queue_worker_queue": queue,
                "django_lightweight_queue_worker_num": str(worker_num),
            }
        }
        for index, (queue, worker_num) in enumerate(worker_queue_and_counts, start=1)
    ]


def metrics_http_server(worker_queue_and_counts):
    config_response = json.dumps(
        get_config_response(worker_queue_and_counts),
        sort_keys=True,
        indent=4,
    ).encode('utf-8')

    class RequestHandler(MetricsHandler, object):

        def do_GET(self):
            if self.path == "/worker_config":
                self.send_response(200)
                self.end_headers()

                return self.wfile.write(config_response)

            return super(RequestHandler, self).do_GET()

    class MetricsServer(threading.Thread):
        def __init__(self, *args, **kwargs):
            super(MetricsServer, self).__init__(*args, **kwargs)

        def run(self):
            httpd = HTTPServer(('0.0.0.0', app_settings.PROMETHEUS_START_PORT), RequestHandler)
            httpd.timeout = 2

            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass

    return MetricsServer(name="Master Prometheus metrics server", daemon=True)
