from django.utils.functional import cached_property

from . import app_settings
from .cron_scheduler import CRON_QUEUE_NAME


class Machine(object):
    """
    Dummy machine class to contain documentation.

    Implementations may extend this class if desired, though this
    is not required.
    """

    @property
    def run_cron(self):
        """
        Returns a `bool` for whether or not a runner on this machine should
        run the cron queue.
        """
        raise NotImplementedError()

    @property
    def worker_names(self):
        """
        Returns a list of tuples of (queue_name, worker_num) for the workers
        which should run on this machine. Worker numbers start at 1.

        Implemetations should be efficient even if this is called several times.
        """
        raise NotImplementedError()


def get_workers_names(machine_number, machine_count, only_queue):
    """
    Determine the workers to run on a given machine in a pool of a known size.
    """

    worker_names = []

    # Iterate over all the possible workers which will be run in the pool,
    # choosing only those which should be run on this machine.
    job_number = 1

    for queue, num_workers in sorted(app_settings.WORKERS.iteritems()):
        if only_queue and only_queue != queue:
            continue

        for worker_num in range(1, num_workers + 1):
            if (job_number % machine_count) + 1 == machine_number:
                worker_names.append((queue, worker_num))

            job_number += 1

    return worker_names


class PooledMachine(Machine):
    """
    A machine which behaves as part of a pool.

    It relies on being given information about the pool which it uses to
    determine its position within the pool and thus which queues to run.
    """

    def __init__(self, machine_number, machine_count, only_queue):
        self.machine_number = machine_number
        self.machine_count = machine_count
        self.only_queue = only_queue

    @property
    def run_cron(self):
        return self.machine_number == 1 and (
            not self.only_queue or self.only_queue == CRON_QUEUE_NAME
        )

    @cached_property
    def worker_names(self):
        return get_workers_names(
            self.machine_number,
            self.machine_count,
            self.only_queue,
        )


class DirectlyConfiguredMachine(Machine):
    """
    A machine which is configured by an explicitly passed in configuration file.

    This class assumes that the loading of the settings from that configuration
    file has already been handled.
    """
    @property
    def run_cron(self):
        return False

    @cached_property
    def worker_names(self):
        return [
            (queue, worker_number)
            for queue, num_workers in sorted(app_settings.WORKERS.iteritems())
            for worker_number in range(num_workers)
        ]
