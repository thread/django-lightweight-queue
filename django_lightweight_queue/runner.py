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
    # Set a dummy title now; multiprocessing will create an extra process
    # which will inherit it - we'll set the real title afterwards
    set_process_title("Internal master process")

    # Use a multiprocessing.Queue to communicate back to the master if/when
    # children should be killed.
    back_channel = multiprocessing.Queue()

    set_process_title("Master process")

    if machine.configure_cron:
        # Load the cron scheduling configuration and setup the worker numbers for it,
        # even if we're not running cronjobs, as it changes the queue count.
        cron_config = get_cron_config()
        ensure_queue_workers_for_config(cron_config)

    # Some backends may require on-startup logic per-queue, initialise a dummy
    # backend per queue to do so. Note: we need to do this after any potential
    # calls to `ensure_queue_workers_for_config` so that all the workers
    # (including the implicit cron ones) have been configured.
    queues_to_startup = set(queue for queue, _ in machine.worker_names)
    for queue in queues_to_startup:
        log.info("Running startup for queue %s", queue)
        backend = get_backend(queue)
        backend.startup(queue)

    # Use shared state to communicate "exit after next job" to the children
    running = multiprocessing.Value('d', 1)

    # Note: we deliberately configure our hanling of SIGTERM _after_ the
    # startup processes have happened; this ensures that the startup processes
    # (which could take a long time) are naturally interupted by the signal.
    def handle_term(signum, stack):
        log.info("Caught TERM signal")
        set_process_title("Master process exiting")
        running.value = 0
    signal.signal(signal.SIGTERM, handle_term)

    if machine.run_cron:
        cron_scheduler = CronScheduler(
            running,
            log.level,
            log_filename_fn(CRON_QUEUE_NAME),
            cron_config,
        )
        cron_scheduler.start()

    workers = {x: None for x in machine.worker_names}

    if app_settings.ENABLE_PROMETHEUS:
        start_master_http_server(running, machine.worker_names)

    while running.value:
        for index, (queue, worker_num) in enumerate(machine.worker_names, start=1):
            worker = workers[(queue, worker_num)]

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
                    index,
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
            except (Empty, EOFError):
                break

            worker = workers[(queue, worker_num)]

            kill_after = None
            if timeout is not None:
                kill_after = time.time() + timeout

            log.debug(
                "Setting kill_after=%r and sigkill_on_stop=%r for %s",
                kill_after,
                sigkill_on_stop,
                worker.name,
            )
            worker.kill_after = kill_after
            worker.sigkill_on_stop = sigkill_on_stop

        time.sleep(1)

    for worker in workers.values():
        if worker is None:
            # the master was killed before this worker was even started
            continue

        if worker.sigkill_on_stop:
            log.info("Sending SIGKILL to %s", worker.name)
            try:
                os.kill(worker.pid, signal.SIGKILL)
            except OSError:
                pass

        log.info("Waiting for %s to terminate", worker.name)
        worker.join()

    log.info("All processes finished; returning")
