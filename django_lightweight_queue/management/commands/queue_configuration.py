from django.core.management.base import NoArgsCommand

from ... import app_settings

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
