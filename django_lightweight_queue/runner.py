import sys
import time
import signal
import subprocess

from . import app_settings
from .utils import get_backend, set_process_title
from .exposition import metrics_http_server
from .cron_scheduler import (
    CronScheduler,
    get_cron_config,
    ensure_queue_workers_for_config,
)


def runner(touch_filename_fn, machine, logger):
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
        logger.debug("Running startup for queue {}".format(queue))
        backend = get_backend(queue)
        backend.startup(queue)

    # Note: we deliberately configure our handling of SIGTERM _after_ the
    # startup processes have happened; this ensures that the startup processes
    # (which could take a long time) are naturally interupted by the signal.
    def handle_term(signum, stack):
        nonlocal running
        logger.debug("Caught TERM signal")
        set_process_title("Master process exiting")
        running = False
    signal.signal(signal.SIGTERM, handle_term)

    if machine.run_cron:
        # Load the cron scheduling configuration explicitly, to account for the
        # case where we want to run the cron but not configure it. This can
        # happen if our caller has already done the configuration.
        cron_config = get_cron_config()
        cron_scheduler = CronScheduler(cron_config)
        cron_scheduler.start()

    workers = {x: None for x in machine.worker_names}

    if app_settings.ENABLE_PROMETHEUS:
        metrics_server = metrics_http_server(machine.worker_names)
        metrics_server.start()

    while running:
        for index, (queue, worker_num) in enumerate(machine.worker_names, start=1):
            worker = workers[(queue, worker_num)]

            # Ensure that all workers are now running (idempotent)
            if worker is None or worker.poll() is not None:
                if worker is None:
                    logger.info(
                        "Starting worker #{} for {}".format(worker_num, queue),
                        extra={
                            'worker': worker_num,
                            'queue': queue,
                        },
                    )
                else:
                    logger.info(
                        "Starting missing worker {} (exit code was: {})".format(
                            worker.name,
                            worker.returncode,
                        ),
                        extra={
                            'worker': worker_num,
                            'queue': queue,
                            'exit_code': worker.returncode,
                        },
                    )

                args = [
                    sys.executable,
                    # manage.py
                    sys.argv[0],
                    'queue_worker',
                    queue,
                    str(worker_num),
                    '--prometheus-port',
                    str(app_settings.PROMETHEUS_START_PORT + index),
                ]

                touch_filename = touch_filename_fn(queue)
                if touch_filename is not None:
                    args.extend([
                        '--touch-file',
                        touch_filename,
                    ])

                worker = subprocess.Popen(args)
                worker.name = "{}/{}".format(queue, worker_num)

                workers[(queue, worker_num)] = worker

        time.sleep(1)

    def signal_workers(signum):
        for worker in workers.values():
            if worker is None:
                continue

            try:
                worker.send_signal(signum)
            except OSError:
                pass

    # SIGUSR2 all the workers. This sets a flag asking them to shut down
    # gracefully, or kills them immediately if they are receptive to that
    # sort of abuse.
    signal_workers(signal.SIGUSR2)

    for worker in workers.values():
        if worker is None:
            continue

        logger.info("Waiting for {} to terminate".format(worker.name))
        worker.wait()

    logger.info("All processes finished")
