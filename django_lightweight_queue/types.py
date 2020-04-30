from types import TracebackType
from typing import Any, Dict, Tuple, Union, NewType, Optional

from typing_extensions import Protocol

QueueName = NewType('QueueName', str)
WorkerNumber = NewType('WorkerNumber', int)

SysExcInfoType = Union[
    Tuple[type, BaseException, Optional[TracebackType]],
    Tuple[None, None, None],
]

_ExcInfoType = Union[None, bool, SysExcInfoType, BaseException]


class Logger(Protocol):
    def log(
        self,
        level: int,
        msg: str,
        *args: Any,
        exc_info: _ExcInfoType = ...,
        stack_info: bool = ...,
        extra: Optional[Dict[str, Any]] = ...,
        **kwargs: Any
    ) -> None:
        ...

    def debug(
        self,
        msg: str,
        *args: Any,
        exc_info: _ExcInfoType = ...,
        stack_info: bool = ...,
        extra: Optional[Dict[str, Any]] = ...,
        **kwargs: Any
    ) -> None:
        ...

    def info(
        self,
        msg: str,
        *args: Any,
        exc_info: _ExcInfoType = ...,
        stack_info: bool = ...,
        extra: Optional[Dict[str, Any]] = ...,
        **kwargs: Any
    ) -> None:
        ...

    def warning(
        self,
        msg: str,
        *args: Any,
        exc_info: _ExcInfoType = ...,
        stack_info: bool = ...,
        extra: Optional[Dict[str, Any]] = ...,
        **kwargs: Any
    ) -> None:
        ...

    def error(
        self,
        msg: str,
        *args: Any,
        exc_info: _ExcInfoType = ...,
        stack_info: bool = ...,
        extra: Optional[Dict[str, Any]] = ...,
        **kwargs: Any
    ) -> None:
        ...

    def exception(
        self,
        msg: str,
        *args: Any,
        exc_info: _ExcInfoType = ...,
        stack_info: bool = ...,
        extra: Optional[Dict[str, Any]] = ...,
        **kwargs: Any
    ) -> None:
        ...
