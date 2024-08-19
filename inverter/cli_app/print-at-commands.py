import rich_click
import rich_click as click


from cli_base.cli_tools.verbosity import OPTION_KWARGS_VERBOSE, setup_logging
from rich import get_console, print  # noqa
from rich.table import Table
from inverter.api import Inverter, fetch_inverter_versions, set_current_time
from inverter.cli_app import cli, option_kwargs_ip, option_kwargs_port, user_settings
from inverter.connection import InverterSock
from inverter.definitions import get_definition_names
from inverter.user_settings import make_config



@cli.command()
@click.argument('commands', nargs=-1)
@click.option('--ip', **option_kwargs_ip)
@click.option('--port', **option_kwargs_port)
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def print_at_commands(ip, port, commands, verbosity: int):
    """
    Print one or more AT command values from Inverter.

    Use all known AT commands, if no one is given, e.g.:

    .../inverter-connect$ ./cli.py print-at-commands

    Or specify one or more AT-commands, e.g.:

    .../inverter-connect$ ./cli.py print-at-commands WEBVER
    .../inverter-connect$ ./cli.py print-at-commands WEBVER WEBU

    e.g.: Set NTP server, enable NTP and check the values:

    .../inverter-connect$ ./cli.py print-at-commands NTPSER=192.168.1.1 NTPEN=on NTPSER NTPEN

    wait a while and request the current date time:

    .../inverter-connect$ ./cli.py print-at-commands NTPTM

    (Note: The prefix "AT+" will be added to every command)
    """
    setup_logging(verbosity=verbosity)

    if not commands:
        commands = (
            'KEY',  # Set/Get Device Password
            'VER',
            'BVER',  # bootloader version
            'HWVER',  # hardware version
            'WEBVER',  # web version
            'YZVER',  # Firmware version
            'PING',
            'YZWAKEYCTL',
            'YZLOG',
            'YZAPP',
            # 'YZAPSTAT', # (doesn't work!)
            'YZEXPFUN',
            'MID',
            # 'CFGRD',  # current system config (doesn't work!)
            # 'SMEM',  # system memory stat (doesn't work!)
            'TIME',
            'ADDRESS',  # Set/Get Device Address
            'KEY',
            'NDBGS',  # Set/Get Debug Status
            'WIFI',  # Set/Get WIFI status: Power up: "WIFI=UP" Power down: "WIFI=DOWN"
            'WMODE',  # Set/Get the WIFI Operation Mode (AP or STA)
            'WEBU',  # Set/Get the Login Parameters of WEB page
            'WAP',  # Set/Get the AP parameters
            'WSSSID',  # Set/Get the AP's SSID of WIFI STA Mode
            'WSKEY',  # Set/Get the Security Parameters of WIFI STA Mode
            'WAKEY',  # Set/Get the Security Parameters of WIFI AP Mode
            'TXPWR',  # Set/Get wifi rf tx power'
            'WANN',  # Set/Get The WAN setting if in STA mode.
            'LANN',  # Set/Get The LAN setting if in ADHOC mode.
            'UPURL',  # Set/Get the path of remote upgrade
            'WAPMXSTA',  # Set/Get the Max Number Of Sta Connected to Ap
            'WSCAN',  # Get The AP site Survey (only for STA Mode).
            'NTPTM',  # NTP date time? e.g.: "1970-1-1  0:3:9  Thur"
            'NTPSER',  # set/query NTP server, e.g.: "NTPSER=192.168.1.1"
            'NTPRF',  # NTP request interval in min (?)
            'NTPEN',  # Enable/Disable NTP Server
            'WSDNS',  # Set/Get the DNS Server address
            'DEVICENUM',  # Set/Get Device Link Num
            'DEVSELCTL',  # Set/Get Web Device List Info
        )

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

        print('Fetch', end='...')
        results = []
        for command in commands:
            print(f'[yellow]{command}', end='')
            result: str = inv_sock.cleaned_at_command(command)
            results.append(dict(command=command, result=result))
            print(',', end='')

    if verbosity > 1:
        pprint(results)

    console = get_console()
    console.print('\n')
    console.rule()

    table = Table(title='AT-command results')
    table.add_column('Counter', justify='right')
    table.add_column('Command', justify='right')
    table.add_column('[green]Result', justify='left', style='green')

    for offset, result in enumerate(results):
        table.add_row(
            str(offset + 1),  # Counter
            f'[grey]AT+[/grey][bold][yellow]{result["command"]}',
            result['result'],
        )

    console.print(table)
