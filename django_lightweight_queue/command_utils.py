import warnings
from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandParser

from .utils import load_extra_settings
from .constants import SETTING_NAME_PREFIX


class CommandWithExtraSettings(BaseCommand):
    """
    Base class for handling `--extra-settings`.

    Derived classes must call `handle_extra_settings` at the top of their
    `handle` method. For example:

        class Command(CommandWithExtraSettings):
            def handle(self, **options: Any) -> None:
                super().handle_extra_settings(**options)
                ...
    """

    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)

        extra_settings_group = parser.add_mutually_exclusive_group()
        extra_settings_group.add_argument(
            '--config',
            action='store',
            default=None,
            help="The path to an additional django-style config file to load "
                 "(this spelling is deprecated in favour of '--extra-settings')",
        )
        extra_settings_group.add_argument(
            '--extra-settings',
            action='store',
            default=None,
            help="The path to an additional django-style settings file to load. "
                 f"{SETTING_NAME_PREFIX}* settings discovered in this file will "
                 "override those from the default Django settings.",
        )

    def handle_extra_settings(
        self,
        *,
        config: Optional[str] = None,
        extra_settings: Optional[str],
        **_: Any
    ) -> Optional[str]:
        """
        Load extra settings if there are any.

        Returns the filename (if any) of the extra settings that have been loaded.
        """

        if config is not None:
            warnings.warn(
                "Use of '--config' is deprecated in favour of '--extra-settings'.",
                category=DeprecationWarning,
            )
            extra_settings = config

        # Configuration overrides
        if extra_settings is not None:
            load_extra_settings(extra_settings)

        return extra_settings
