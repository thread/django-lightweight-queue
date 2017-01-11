from django.core.management.base import BaseCommand

from ... import app_settings
from ...utils import get_backend, load_extra_config
from ...cron_scheduler import get_cron_config


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--config', action='store', default=None,
            help="The path to an additional django-style config file to load")

    def handle(self, **options):
        # Configuration overrides
        extra_config = options['config']
        if extra_config is not None:
            load_extra_config(extra_config)

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

        for x in get_cron_config():
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
