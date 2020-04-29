import datetime
import unittest

from django_lightweight_queue.job import Job


class JobTests(unittest.TestCase):
    longMessage = True

    def create_job(
        self,
        path='path',
        args=('args',),
        kwargs=None,
        timeout=None,
        sigkill_on_stop=False,
        created_time=None,
    ):
        if created_time is None:
            created_time = self.start_time

        job = Job(path, args, kwargs, timeout, sigkill_on_stop)
        job.created_time = created_time

        return job

    def setUp(self):
        super(JobTests, self).setUp()
        self.start_time = datetime.datetime.utcnow()

    def test_identity_same_created_time(self):
        job1 = self.create_job(
            created_time=datetime.datetime(2018, 1, 1),
        )

        job2 = self.create_job(
            created_time=datetime.datetime(2018, 1, 1),
        )

        self.assertEqual(
            job1.identity_without_created(),
            job2.identity_without_created(),
            "Identities should match",
        )

    def test_identity_different_created_time(self):
        job1 = self.create_job(
            created_time=datetime.datetime(2018, 1, 1),
        )

        job2 = self.create_job(
            created_time=datetime.datetime(2018, 2, 2),
        )

        self.assertEqual(
            job1.identity_without_created(),
            job2.identity_without_created(),
            "Identities should match",
        )

    def test_identity_different_args(self):
        job1 = self.create_job(
            args=('args1',),
        )

        job2 = self.create_job(
            args=('args2',),
        )

        self.assertNotEqual(
            job1.identity_without_created(),
            job2.identity_without_created(),
            "Identities should match",
        )
