from django.core.management.base import NoArgsCommand

from ... import app_settings
from ...cron_scheduler import get_config

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        print "django-lightweight-queue"
        print "========================"
        print
        print "{0:<15} {1:>5}".format("Queue name", "Concurrency")
        print "-" * 27

        for k, v in app_settings.WORKERS.iteritems():
            print " {0:<14} {1}".format(k, v)

        print
        print "Middleware:"
        for x in app_settings.MIDDLEWARE:
            print " * %s" % x

        print
        print "Backend: %s" % app_settings.BACKEND

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
