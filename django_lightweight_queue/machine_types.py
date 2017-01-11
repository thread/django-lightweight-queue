from django.utils.functional import cached_property

from .cron_scheduler import CRON_QUEUE_NAME
from .runner import get_workers_names


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
