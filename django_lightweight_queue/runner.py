import os
import time
import signal
import multiprocessing

try:
    from queue import Empty
except ImportError:
    from Queue import Empty

from . import app_settings
from .utils import set_process_title, get_backend
from .worker import Worker
from .exposition import start_master_http_server
from .cron_scheduler import CronScheduler, CRON_QUEUE_NAME, get_cron_config, \
    ensure_queue_workers_for_config


def runner(log, log_filename_fn, touch_filename_fn, machine):
    set_process_title("Master process")

    if machine.configure_cron:
        # Load the cron scheduling configuration and setup the worker numbers for it,
        # even if we're not running cronjobs, as it changes the queue count.
        cron_config = get_cron_config()
        ensure_queue_workers_for_config(cron_config)

    running = True

    # Some backends may require on-startup logic per-queue, initialise a dummy
    # backend per queue to do so. Note: we need to do this after any potential
    # calls to `ensure_queue_workers_for_config` so that all the workers
    # (including the implicit cron ones) have been configured.
    queues_to_startup = set(queue for queue, _ in machine.worker_names)
    for queue in queues_to_startup:
        log.info("Running startup for queue %s", queue)
        backend = get_backend(queue)
        backend.startup(queue)

    # Note: we deliberately configure our handling of SIGTERM _after_ the
    # startup processes have happened; this ensures that the startup processes
    # (which could take a long time) are naturally interupted by the signal.
    def handle_term(signum, stack):
        nonlocal running
        log.info("Caught TERM signal")
        set_process_title("Master process exiting")
        running = False
    signal.signal(signal.SIGTERM, handle_term)

    if machine.run_cron:
        cron_scheduler = CronScheduler(
            log.level,
            log_filename_fn(CRON_QUEUE_NAME),
            cron_config,
        )
        cron_scheduler.start()

    workers = {x: None for x in machine.worker_names}

    if app_settings.ENABLE_PROMETHEUS:
        start_master_http_server(running, machine.worker_names)

    while running:
        for index, (queue, worker_num) in enumerate(machine.worker_names, start=1):
            worker = workers[(queue, worker_num)]

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
                    index,
                    worker_num,
                    log.level,
                    log_filename_fn('%s.%s' % (queue, worker_num)),
                    touch_filename_fn(queue),
                )

                workers[(queue, worker_num)] = worker
                worker.start()

        time.sleep(1)

    if machine.run_cron:
        # The cron scheduler is always safe to kill.
        os.kill(cron_scheduler.pid, signal.SIGKILL)
        cron_scheduler.join()

    def signal_workers(signum):
        for worker in workers.values():
            if worker is None:
                continue

            try:
                os.kill(worker.pid, signum)
            except OSError:
                pass

    # SIGUSR2 all the workers. This sets a flag asking them to shut down
    # gracefully, or kills them immediately if they are receptive to that
    # sort of abuse.
    signal_workers(signal.SIGUSR2)

    for worker in workers.values():
        if worker is None:
            continue
        log.info("Waiting for %s to terminate", worker.name)
        worker.join()

    log.info("All processes finished; returning")
