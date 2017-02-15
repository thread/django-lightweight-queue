# Django Lightweight Queue

DLQ is a lightweight & modular queue and cron system for Django.

## Basic Usage

``` python
import time
from django_lightweight_queue import task

# Define a task
@task()
def long_running_task(first_arg, second_arg):
    time.sleep(first_arg * second_arg)

# Request that the task be executed at some point
long_running_task(4, second_arg=9)
```

See the docstring on the [`task`](django_lightweight_queue/task.py) decorator
for more details.

## Configuration

Configuration options should be placed in the usual Django settings files,
prefixed with `LIGHTWEIGHT_QUEUE_`, for example:
``` python
LIGHTWEIGHT_QUEUE_BACKEND = 'django_lightweight_queue.backends.redis.RedisBackend'
```

If desired, specific configuration overrides can be placed in a standalone python
file which passed on the command line.

For example, given a `special.py` containing:
``` python
LIGHTWEIGHT_QUEUE_REDIS_PORT = 12345
```
and then running:
```
$ python manage.py queue_runner --config=special.py
```
will result in the runner to use the settings from the specified configuration
file in preference to settings from the Django environment. Any settings not
present in the specified file are inherited from the global configuration.

### Backends

There are three built-in backends:
- Synchronous (the default): executes the task inline, without any actual queuing
- Redis: executes tasks at-most-once using [Redis][redis] for storage of the
  enqueued tasks
- Reliable Redis: executes tasks at-least-once using [Redis][redis] for storage
  of the enqueued tasks

[redis]: https://redis.io/

## Running Workers

The queue runner is implemented as a Django management command:
```
$ python manage.py queue_runner
```

Workers can be shared over multiple hosts by telling each runner that it is part
of a pool:

```
$ python manage.py queue_runner --machine 2 --of 4
```

Alternatively a runner can be told explicitly which configuration to use:
```
$ python manage.py queue_runner --exact-configuration --config=special.py
```
When using `--exact-configuration` the number of workers is configured exactly,
rather than being treated as the configuration for a pool. Additionally,
exactly-configured runners will _not_ run any cron workers.

### Example

Given a Django configuration containing:
``` python
LIGHTWEIGHT_QUEUE_WORKERS = {
    'queue1': 3,
}
```
and a `special.py` containing:
``` python
LIGHTWEIGHT_QUEUE_WORKERS = {
    'queue1': 2,
}
```
Running:
```
$ python manage.py queue_runner --machine 1 --of 3 # or,
$ python manage.py queue_runner --machine 2 --of 3 # or,
$ python manage.py queue_runner --machine 3 --of 3
```
will result in one worker for `queue1` on the current machine, while:
```
$ python manage.py queue_runner --exact-configuration --config=special.py
```
will result in two workers on the current machine.

## Cron Tasks

DLQ supports the use of a cron-like specification of Django management commands
to be run at certain times.

To specify that a management command should be run at a given time, place a
`cron.py` file in the root folder of the Django app which defines the command
and which contains a `CONFIG` variable:

``` python
CONFIG = (
    {
        'command': 'my_cron_command',
        # Day values 1-7 to match datetime.datetime.utcnow().isoweekday()
        'days': '*',
        'hours': '*',
        'minutes': '*',
        # Equivalent behaviour to the kwarg to `task` of the same name
        'sigkill_on_stop': True,
    },
)
```
