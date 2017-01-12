from django.core.management.base import BaseCommand

from ... import app_settings
from ...utils import get_backend
from ...cron_scheduler import get_config


class Command(BaseCommand):
    def handle(self, **options):
        print "django-lightweight-queue"
        print "========================"
        print
        print "{0:<55} {1:<5} {2}".format("Queue name", "Concurrency", "Backend")
        print "-" * 27

        for k, v in app_settings.WORKERS.iteritems():
            print " {0:<54} {1:<5} {2}".format(
                k,
                v,
                get_backend(k).__class__.__name__,
            )

        print
        print "Middleware:"
        for x in app_settings.MIDDLEWARE:
            print " * %s" % x

        print
        print "Cron configuration"

        for x in get_config():
            print
            for k in (
                'command',
                'command_args',
                'hours',
                'minutes',
                'queue',
                'timeout',
                'sigkill_on_stop',
            ):
                print "% 20s: %s" % (k, x.get(k, '-'))
