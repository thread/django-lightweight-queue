from typing import TypeVar, Callable, Iterable, NamedTuple

T = TypeVar('T')

Logger = NamedTuple('Logger', [
    ('info', Callable[[str], None]),
    ('progress', Callable[[Iterable[T]], Iterable[T]]),
])

NULL_LOGGER = Logger(lambda x: None, lambda x: x)
