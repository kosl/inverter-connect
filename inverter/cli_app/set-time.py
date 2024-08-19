import time
import rich_click
import rich_click as click


from cli_base.cli_tools.verbosity import OPTION_KWARGS_VERBOSE, setup_logging
from rich import get_console, print  # noqa
from inverter.api import Inverter, fetch_inverter_versions, set_current_time
from inverter.cli_app import cli, option_kwargs_ip, option_kwargs_port, user_settings
from inverter.connection import InverterSock
from inverter.user_settings import make_config
from inverter.utilities.cli import convert_address_option, print_register

@cli.command()
@click.option('--ip', **option_kwargs_ip)
@click.option('--port', **option_kwargs_port)
@click.option('--register', default="0x16", help='Start address', show_default=True)
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def set_time(ip, port, register, verbosity: int):
    """
    Set current date time in the inverter device.

    Default start address is 0x16, so that this will be filled:
        0x16 - year + month
        0x17 - day + hour
        0x18 - minute + second
    """
    setup_logging(verbosity=verbosity)

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

        set_current_time(inv_sock=inv_sock, address=address, verbose=True)

        print('\nRead register...')
        time.sleep(1)
        print_register(inv_sock, start_register=address, length=3)

        print('\nCheck time by request "AT+NTPTM"', end='...')
        time.sleep(1)
        result: str = inv_sock.cleaned_at_command(command='NTPTM')
        print(f'[green]{result}')

