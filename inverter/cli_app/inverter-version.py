import rich_click
import rich_click as click


from cli_base.cli_tools.verbosity import OPTION_KWARGS_VERBOSE, setup_logging
from rich import get_console, print  # noqa
from inverter.api import Inverter, fetch_inverter_versions
from inverter.cli_app import cli, option_kwargs_ip, option_kwargs_port, user_settings
from inverter.user_settings import make_config
from inverter.connection import InverterSock
from inverter.data_types import InverterRegisterVersionInfo
from inverter.utilities.cli import print_inverter_versions


@cli.command()
@click.option('--ip', **option_kwargs_ip)
@click.option('--port', **option_kwargs_port)
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def inverter_version(ip, port, verbosity: int):
    """
    Print all version information of the inverter
    """
    setup_logging(verbosity=verbosity)

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

        infos = [
            InverterRegisterVersionInfo(name='Control Board Firmware', register=0x000D),
            InverterRegisterVersionInfo(name='Communication Board Firmware', register=0x000E),
            InverterRegisterVersionInfo(name='Communication Protocol', register=0x0012),
        ]
        results = fetch_inverter_versions(inv_sock=inv_sock, infos=infos)

    print_inverter_versions(results)
