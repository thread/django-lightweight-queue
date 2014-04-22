import time
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

    def dequeue(self, queue, timeout):
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, data FROM %s WHERE queue = %%s
            ORDER BY created ASC LIMIT 1
        """ % connection.ops.quote_name(self.TABLE), (queue,))

        try:
            id_, data = cursor.fetchall()[0]
        except (IndexError, ProgrammingError):
            time.sleep(timeout)
            return

        cursor.execute("""
            DELETE FROM %s WHERE id = %%s
        """ % connection.ops.quote_name(self.TABLE), (id_,))

        try:
            return Job.from_json(data)
        except TypeError:
            pass
