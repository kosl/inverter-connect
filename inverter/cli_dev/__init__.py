"""
    CLI for development
"""
import logging
import os
import sys
from pathlib import Path

import rich_click as click
from rich.console import Console
from rich.traceback import install as rich_traceback_install

#import tomlkit
from cli_base.autodiscover import import_all_files
from cli_base.cli_tools.dev_tools import run_coverage, run_tox, run_unittest_cli
#from cli_base.cli_tools.subprocess_utils import verbose_check_call
from cli_base.toml_settings.api import TomlSettings
from cli_base.toml_settings.serialize import dataclass2toml
#from manageprojects.utilities import code_style
#from manageprojects.utilities.publish import publish_package
from manageprojects.utilities.version_info import print_version
from rich import print  # noqa; noqa
from rich_click import RichGroup
from tomlkit import TOMLDocument

import inverter
from inverter import constants
from inverter.constants import PACKAGE_ROOT, SETTINGS_DIR_NAME, SETTINGS_FILE_NAME
from inverter.user_settings import UserSettings


logger = logging.getLogger(__name__)


OPTION_ARGS_DEFAULT_TRUE = dict(is_flag=True, show_default=True, default=True)
OPTION_ARGS_DEFAULT_FALSE = dict(is_flag=True, show_default=True, default=False)
ARGUMENT_EXISTING_DIR = dict(
    type=click.Path(exists=True, file_okay=False, dir_okay=True, readable=True, path_type=Path)
)
ARGUMENT_NOT_EXISTING_DIR = dict(
    type=click.Path(
        exists=False,
        file_okay=False,
        dir_okay=True,
        readable=False,
        writable=True,
        path_type=Path,
    )
)
ARGUMENT_EXISTING_FILE = dict(
    type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True, path_type=Path)
)


class ClickGroup(RichGroup):  # FIXME: How to set the "info_name" easier?
    def make_context(self, info_name, *args, **kwargs):
        info_name = './dev-cli.py'
        return super().make_context(info_name, *args, **kwargs)


@click.group(
    cls=ClickGroup,
    epilog=constants.CLI_EPILOG,
)
def cli():
    pass



@click.command()
def install():
    """
    Run pip-sync and install 'inverter' via pip as editable.
    """
    verbose_check_call('pip-sync', PACKAGE_ROOT / 'requirements.dev.txt')
    verbose_check_call('pip', 'install', '--no-deps', '-e', '.')


cli.add_command(install)

# Register all click commands, just by import all files in this package:
import_all_files(package=__package__, init_file=__file__)

@click.command()
def version():
    """Print version and exit"""
    # Pseudo command, because the version always printed on every CLI call ;)
    sys.exit(0)


cli.add_command(version)


######################################################################################################
@click.command()
@click.option('--force', **OPTION_ARGS_DEFAULT_FALSE)
def create_default_settings(force):
    """
    Create a default user settings file. (Used by CI pipeline ;)
    """
    if not force and 'CI' not in os.environ:
        print('We are not running in CI pipeline and "--force" not used -> Abort.')
        sys.exit(-1)

    settings_dataclass = UserSettings()
    toml_settings = TomlSettings(
        dir_name=SETTINGS_DIR_NAME,
        file_name=SETTINGS_FILE_NAME,
        settings_dataclass=settings_dataclass,
    )

    settings_path = toml_settings.file_path
    if settings_path.is_file():
        print(f'[green]Use settings file already exists here: {settings_path}')
        return

    document: TOMLDocument = dataclass2toml(instance=settings_dataclass)
    doc_str = tomlkit.dumps(document, sort_keys=False)

    settings_path.write_text(doc_str, encoding='UTF-8')
    print(f'[green]Default settings file created here: {settings_path}')


cli.add_command(create_default_settings)

######################################################################################################


def main():
    print_version(inverter)

    console = Console()
    rich_traceback_install(
        width=console.size.width,  # full terminal width
        show_locals=True,
        suppress=[click],
        max_frames=2,
    )


    if len(sys.argv) >= 2:
        # Check if we can just pass a command call to origin CLI:
        command = sys.argv[1]
        command_map = {
            'test': run_unittest_cli,
            'tox': run_tox,
            'coverage': run_coverage,
        }
        if real_func := command_map.get(command):
            real_func(argv=sys.argv, exit_after_run=True)

    # Execute Click CLI:
    cli()
