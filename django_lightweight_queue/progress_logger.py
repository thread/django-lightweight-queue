from typing import TypeVar, Callable, Iterable, NamedTuple

T = TypeVar('T')

ProgressLogger = NamedTuple('ProgressLogger', [
    ('info', Callable[[str], None]),
    ('progress', Callable[[Iterable[T]], Iterable[T]]),
])

NULL_PROGRESS_LOGGER = ProgressLogger(lambda x: None, lambda x: x)
