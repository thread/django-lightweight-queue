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
When using `--exact-configuration` the settings from Django are overwritten with
any in the specified configuration file, settings not present in the specified
file are inherited from the global configuration.

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
        # Equivalent the kwarg to `task` of the same name
        'sigkill_on_stop': True,
    },
)
```
