import time
import select
import datetime

from django.db import connection, models, ProgrammingError

from ..job import Job

class DatabaseBackend(object):
    TABLE = 'django_lightweight_queue'

    FIELDS = (
        models.AutoField(name='id', primary_key=True),
        models.CharField(name='queue', max_length=255),
        models.TextField(name='data'),
        models.DateTimeField(name='created'),
    )

    HAS_PUBSUB = bool(connection.vendor == 'postgresql')

    def __init__(self):
        qn = connection.ops.quote_name

        sql = []
        for x in self.FIELDS:
            sql.append(' '.join((
                qn(x.name),
                x.db_type(connection=connection),
                'PRIMARY KEY' if x.primary_key else '',
            )))

        cursor = connection.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS %s (\n%s\n);' % (
            qn(self.TABLE),
            ',\n'.join(sql),
        ))

        try:
            cursor.execute('CREATE INDEX %s ON %s (%s, %s)' % (
                qn('%s_idx' % self.TABLE),
                qn(self.TABLE),
                qn('queue'),
                qn('created'),
            ))
        except ProgrammingError:
            # "IF NOT EXISTS" is not portable, so we just fail to create it
            pass

        # Don't share connections across fork()
        connection.close()

    def enqueue(self, job, queue):
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO %s (queue, data, created) VALUES (%%s, %%s, %%s)
        """ % connection.ops.quote_name(self.TABLE), (
            queue,
            job.to_json(),
            datetime.datetime.utcnow(),
        ))

        if self.HAS_PUBSUB:
            cursor.execute('NOTIFY "%s:%s"' % (self.TABLE, queue))

    def dequeue(self, queue, timeout):
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, data FROM %s WHERE queue = %%s
            ORDER BY created ASC LIMIT 1
        """ % connection.ops.quote_name(self.TABLE), (queue,))

        try:
            id_, data = cursor.fetchall()[0]
        except (IndexError, ProgrammingError):
            if self.HAS_PUBSUB:
                cursor.execute('LISTEN "%s:%s"' % (self.TABLE, queue))

                c = cursor.connection

                # Wait to see if we hear anything. If we do, we just return
                # earlier than ``timeout`` rather than polling the DB again as
                # we'll be called immediately anyway.
                select.select([c], [], [], timeout)

                # Empty notification queue.
                c.poll()
                while c.notifies:
                    c.notifies.pop()
            else:
                time.sleep(timeout)

            return

        cursor.execute("""
            DELETE FROM %s WHERE id = %%s
        """ % connection.ops.quote_name(self.TABLE), (id_,))

        try:
            return Job.from_json(data)
        except TypeError:
            pass
