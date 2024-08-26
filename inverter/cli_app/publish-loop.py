import time

import rich_click as click
from cli_base.cli_tools.verbosity import OPTION_KWARGS_VERBOSE, setup_logging
from cli_base.toml_settings.exceptions import UserSettingsNotFound
from cli_base.toml_settings.api import TomlSettings
from rich import print  # noqa

import inverter
from inverter.cli_app import cli, option_kwargs_ip, option_kwargs_port, option_kwargs_inverter_name
from inverter.mqtt_handler import InverterMqttHandler
from inverter.user_settings import UserSettings, get_user_settings, get_toml_settings
from ha_services.mqtt4homeassistant.mqtt import get_connected_client
import logging

from ha_services.mqtt4homeassistant.components.sensor import Sensor
from ha_services.mqtt4homeassistant.device import MainMqttDevice, MqttDevice
from ha_services.mqtt4homeassistant.mqtt import get_connected_client

import inverter
from inverter.user_settings import UserSettings, make_config


logger = logging.getLogger(__name__)


@cli.command()
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def test_mqtt_connection(verbosity: int):
    """
    Test connection to MQTT Server
    """
    setup_logging(verbosity=verbosity)
    user_settings: UserSettings = get_user_settings(verbosity=verbosity)


    settings: MqttSettings = user_settings.mqtt
    mqttc = get_connected_client(settings=settings, verbosity=verbosity)
    mqttc.loop_start()
    mqttc.loop_stop()
    mqttc.disconnect()
    print('\n[green]Test succeed[/green], bye ;)')


@cli.command()
@click.option('--ip', **option_kwargs_ip)
@click.option('--port', **option_kwargs_port)
@click.option('--inverter', **option_kwargs_inverter_name)
@click.option('-v', '--verbosity', **OPTION_KWARGS_VERBOSE)
def publish_loop(ip, port, inverter, verbosity: int):
    """
    Publish inverter registers to Home Assistant MQTT
    """
    setup_logging(verbosity=verbosity)
    user_settings: UserSettings = get_user_settings(verbosity=verbosity)


    toml_settings = get_toml_settings()

    config = make_config(
        user_settings=user_settings,
        config_path=toml_settings.file_path.parent,  # e.g.: ~/.config/inverter-connect/
        verbosity=verbosity,
        ip=ip,
        port=port,
        inverter=inverter,
    )
        
    inverter_mqtt_handler = InverterMqttHandler(config=config, user_settings=user_settings, verbosity=verbosity)
    
    while True:
        try:
            inverter_mqtt_handler.publish_loop(verbosity=verbosity)
        except TimeoutError:
            print('Timeout... Retrying in 1 second...')
            time.sleep(1)
        except Exception as e:
            print(f'Error: {e}', type(e))
            print('Retrying in 1 second...')
            time.sleep(1)
