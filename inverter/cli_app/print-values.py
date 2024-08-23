import rich_click
import rich_click as click


from cli_base.cli_tools.verbosity import OPTION_KWARGS_VERBOSE, setup_logging
from cli_base.toml_settings.api import TomlSettings
from rich import get_console, print  # noqa
from inverter.api import Inverter, fetch_inverter_versions, set_current_time
from inverter.cli_app import cli, option_kwargs_ip, option_kwargs_port, user_settings, option_kwargs_inverter_name, option_kwargs_compact
from inverter.user_settings import SystemdServiceInfo, UserSettings, make_config
from inverter.utilities.cli import (
    convert_address_option,
    print_inverter_values,
    print_inverter_versions,
    print_register,
)



@cli.command()
@click.option('--ip', **option_kwargs_ip)
@click.option('--port', **option_kwargs_port)
@click.option('--inverter', **option_kwargs_inverter_name)
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
@click.option('-c', '--compact', **option_kwargs_compact)
def print_values(ip, port, inverter, verbosity: int, compact: bool):
    """
    Print all known register values from Inverter, e.g.:

    .../inverter-connect$ ./cli.py print-values
    """
    setup_logging(verbosity=verbosity)

    print()

    config = make_config(
        user_settings=user_settings,
        verbosity=verbosity,
        ip=ip,
        port=port,
        compact=compact,
        inverter=inverter,
    )

    with Inverter(config=config) as inverter:
        try:
            inverter.connect()
        except ReadInverterError as err:
            print(f'[red]{err}')
            sys.exit(1)

        print('Fetch', end='...')
        values = []
        for value in inverter:
            print(f'[yellow]{value.name}[/yellow],', end='')
            values.append(value)

    if verbosity > 1:
        pprint(values)
    print_inverter_values(values)
