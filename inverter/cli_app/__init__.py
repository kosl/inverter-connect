"""
    CLI for usage
"""

import atexit
import datetime
import logging
import sys

import rich_click as click
from cli_base.autodiscover import import_all_files
from cli_base.cli_tools.version_info import print_version
from cli_base.toml_settings.api import TomlSettings
from rich import get_console, print  # noqa
from rich.console import Console
from rich.traceback import install as rich_traceback_install
from rich_click import RichGroup

import inverter
from inverter import constants
from inverter.constants import SETTINGS_DIR_NAME, SETTINGS_FILE_NAME
from inverter.definitions import get_definition_names
from inverter.user_settings import SystemdServiceInfo, UserSettings, make_config, migrate_old_settings


logger = logging.getLogger(__name__)

toml_settings = TomlSettings(
    dir_name=SETTINGS_DIR_NAME,
    file_name=SETTINGS_FILE_NAME,
    settings_dataclass=UserSettings(),
    not_exist_exit_code=None,  # Don't sys.exit() if settings file not present, yet.
)


try:
    user_settings: UserSettings = toml_settings.get_user_settings(debug=True)
except UserSettingsNotFound:
    # Use default one
    user_settings = UserSettings()


option_kwargs_ip = dict(
    required=True,
    type=str,
    help='IP address of your inverter',
    default=user_settings.inverter.ip or None,  # Don't accept empty string as IP: We need a address ;)
    show_default=True,
)
option_kwargs_port = dict(
    required=True,
    type=int,
    default=user_settings.inverter.port,
    help='Port of inverter services',
    show_default=True,
)
option_kwargs_inverter_name = dict(
    required=True,
    type=click.Choice(get_definition_names(), case_sensitive=False),
    default=user_settings.inverter.name,
    help='Prefix of yaml config files in inverter/definitions/',
    show_default=True,
)
option_kwargs_compact = dict(
    required=False,
    default=False,
    help='Only show the values concerning power generation',
    is_flag=True,
    show_default=False,
)


class ClickGroup(RichGroup):  # FIXME: How to set the "info_name" easier?
    def make_context(self, info_name, *args, **kwargs):
        info_name = './cli.py'
        return super().make_context(info_name, *args, **kwargs)


@click.group(
    cls=ClickGroup,
    epilog=constants.CLI_EPILOG,
)
def cli():
    pass


# Register all click commands, just by import all files in this package:
import_all_files(package=__package__, init_file=__file__)


@cli.command()
def version():
    """Print version and exit"""
    # Pseudo command, because the version always printed on every CLI call ;)
    sys.exit(0)

def exit_func():
    console = get_console()
    console.rule(datetime.datetime.now().strftime('%c'))

    
def main():
    print_version(inverter)

    console = Console()
    rich_traceback_install(
        width=console.size.width,  # full terminal width
        show_locals=True,
        suppress=[click],
        max_frames=2,
    )

    atexit.register(exit_func)

    # Execute Click CLI:
    cli.name = './cli.py'
    cli()
