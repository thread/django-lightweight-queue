import os
import time
import signal
import multiprocessing

from Queue import Empty

from . import app_settings
from .utils import set_process_title, get_backend
from .worker import Worker
from .cron_scheduler import CronScheduler, get_cron_config, ensure_queue_workers_for_config

def runner(log, log_filename_fn, touch_filename_fn, machine_number, machine_count, only_queue=None, num_only_queue_workers=None):
    # Set a dummy title now; multiprocessing will create an extra process
    # which will inherit it - we'll set the real title afterwards
    set_process_title("Internal master process")

    # Use a multiprocessing.Queue to communicate back to the master if/when
    # children should be killed.
    back_channel = multiprocessing.Queue()

    # Use shared state to communicate "exit after next job" to the children
    running = multiprocessing.Value('d', 1)

    set_process_title("Master process")

    def handle_term(signum, stack):
        log.info("Caught TERM signal")
        set_process_title("Master process exiting")
        running.value = 0
    signal.signal(signal.SIGTERM, handle_term)

    # Load the cron scheduling configuration and setup the worker numbers for it,
    # even if we're not running cronjobs, as it changes the queue count.
    cron_config = get_cron_config()
    ensure_queue_workers_for_config(cron_config)

    if machine_number == 1:
        cron_scheduler = CronScheduler(
            running,
            log.level,
            log_filename_fn('cron_scheduler'),
            cron_config,
        )

        if not only_queue or only_queue == 'cron_scheduler':
            cron_scheduler.start()

    workers = {}

    # Some backends may require on-startup logic per-queue, initialise a dummy
    # backend per queue to do so.
    for queue in app_settings.WORKERS.keys():
        if not only_queue or only_queue == queue:
            backend = get_backend(queue)
            backend.startup(queue)

    # Used to determine the parallelism split
    job_number = 1

    for queue, num_workers in sorted(app_settings.WORKERS.iteritems()):
        if only_queue and only_queue != queue:
            continue

        if only_queue and num_only_queue_workers is not None:
            num_workers = num_only_queue_workers

        for x in range(1, num_workers + 1):
            # We don't go out of our way to start workers on startup - we let
            # the "restart if they aren't already running" machinery do its
            # job.
            if (job_number % machine_count) + 1 == machine_number:
                workers[(queue, x)] = None

            job_number += 1

    while running.value:
        for (queue, worker_num), worker in workers.items():

            # Kill any workers that have exceeded their timeout
            if worker and worker.kill_after and time.time() > worker.kill_after:
                log.warning("Sending SIGKILL to %s due to timeout", worker.name)

                try:
                    os.kill(worker.pid, signal.SIGKILL)

                    # Sleep for a bit so we don't start workers constantly
                    time.sleep(0.1)
                except OSError:
                    pass

            # Ensure that all workers are now running (idempotent)
            if worker is None or not worker.is_alive():
                if worker is None:
                    log.info("Starting worker #%d for %s", worker_num, queue)
                else:
                    log.info(
                        "Starting missing worker %s (exit code was: %s)",
                        worker.name,
                        worker.exitcode,
                    )

                worker = Worker(
                    queue,
                    worker_num,
                    back_channel,
                    running,
                    log.level,
                    log_filename_fn('%s.%s' % (queue, worker_num)),
                    touch_filename_fn(queue),
                )

                workers[(queue, worker_num)] = worker
                worker.start()

        while True:
            try:
                log.debug("Checking back channel for items")

                # We don't use the timeout kwarg so that when we get a TERM
                # signal we don't have problems with interrupted system calls.
                msg = back_channel.get_nowait()

                queue, worker_num, timeout, sigkill_on_stop = msg
            except Empty:
                break

            worker = workers[(queue, worker_num)]

            kill_after = None
            if timeout is not None:
                kill_after = time.time() + timeout

            log.debug(
                "Setting kill_after=%r and kill_on_stop=%s for %s",
                worker.name,
                kill_after,
            )
            worker.kill_after = kill_after
            worker.sigkill_on_stop = sigkill_on_stop

        time.sleep(1)

    for worker in workers.values():
        if worker.sigkill_on_stop:
            log.info("Sending SIGKILL to %s", worker.name)
            try:
                os.kill(worker.pid, signal.SIGKILL)
            except OSError:
                pass

        log.info("Waiting for %s to terminate", worker.name)
        worker.join()

    log.info("All processes finished; returning")
