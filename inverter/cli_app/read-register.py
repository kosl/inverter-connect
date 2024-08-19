import rich_click
import rich_click as click


from cli_base.cli_tools.verbosity import OPTION_KWARGS_VERBOSE, setup_logging
from rich import get_console, print  # noqa
from inverter.api import Inverter, fetch_inverter_versions
from inverter.cli_app import cli, option_kwargs_ip, option_kwargs_port, user_settings
from inverter.connection import InverterSock
from inverter.user_settings import make_config
from inverter.utilities.cli import convert_address_option, print_register

@cli.command()
@click.option('--ip', **option_kwargs_ip)
@click.option('--port', **option_kwargs_port)
@click.argument('register')
@click.argument('length', type=click.IntRange(1, 100))
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def read_register(ip, port, register, length, verbosity: int):
    """
    Read register(s) from the inverter

    e.g.: read 3 registers starting from 0x16:

        .../inverter-connect$ ./cli.py read-register 0x16 3

    e.g.: read the first 32 registers:

    .../inverter-connect$ ./cli.py read-register 0 32

    The start address can be pass as decimal number or as hex string, e.g.: 0x123
    """

    setup_logging(verbosity=verbosity)

    print(f'Read {length} register(s) from {register=!r} ({ip}:{port})')
    address = convert_address_option(raw_address=register, debug=bool(verbosity))

    config = make_config(
        user_settings=user_settings,
        verbosity=verbosity,
        ip=ip,
        port=port,
        inverter=None,
    )

    with InverterSock(config) as inv_sock:
        try:
            inv_sock.connect()
        except ReadInverterError as err:
            print(f'[red]{err}')
            sys.exit(1)

        print_register(inv_sock, start_register=address, length=length)
