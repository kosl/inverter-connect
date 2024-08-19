import asyncio
import logging
import time

from cli_base.cli_tools.rich_utils import human_error
from ha_services.mqtt4homeassistant.components.sensor import Sensor
#from ha_services.mqtt4homeassistant.components.binary_sensor import BinarySensor
#from ha_services.mqtt4homeassistant.components.switch import Switch
from ha_services.mqtt4homeassistant.device import  MqttDevice
from ha_services.mqtt4homeassistant.mqtt import get_connected_client
from ha_services.mqtt4homeassistant.utilities.string_utils import slugify
from paho.mqtt.client import Client
#from ha_services.mqtt4homeassistant.converter import values2mqtt_payload
#from ha_services.mqtt4homeassistant.data_classes import HaValue, HaValues
#from ha_services.mqtt4homeassistant.mqtt import HaMqttPublisher
from packaging.version import Version
from rich import print  # noqa

from inverter import __version__
from inverter.api import Inverter
from inverter.constants import ERROR_STR_NO_DATA, DEFAULT_DEVICE_MANUFACTURER
from inverter.daily_reset import DailyProductionReset, DailyProductionResetState
from inverter.data_types import Config, InverterInfo, InverterValue
from inverter.exceptions import ReadInverterError, ReadTimeout, ValidationError
from inverter.user_settings import UserSettings

logger = logging.getLogger(__name__)

class InverterMqttHandler:
    def __init__(self, user_settings: UserSettings, verbosity: int):
        self.user_settings = user_settings
        self.verbosity = verbosity
        self.mqtt_client = get_connected_client(settings=user_settings.mqtt, verbosity=verbosity)
        self.mqtt_client.loop_start()
        self.main_device: MqttDevice|None = None
        self.sensors = list()

    def init_device(self, inverter: Inverter, inverter_info: InverterInfo, inverter_model_name: str, verbosity: int):
        """
        Create sensors from definitions.toml add it to device for later
        update in publish process.
        """
        self.main_device = MqttDevice(
            name='Inverter ' + str(inverter_info.serial),
            uid=str(inverter_info.serial), # Required for multiple inverters to appear as main device
            manufacturer=DEFAULT_DEVICE_MANUFACTURER,
            model=inverter_model_name.upper(),
            sw_version=__version__,
            config_throttle_sec=self.user_settings.mqtt.publish_config_throttle_seconds,
        )
        self.sensors.append(Sensor(
            device=self.main_device,
            name='Loop Running Time',
            uid=slugify('Loop Running Time'),
            device_class=None,
            state_class='measurement',
            unit_of_measurement='sec.',
            suggested_display_precision=0,
        ))
        
    async def publish_loop(self, config: Config, verbosity):

        try:
            with Inverter(config=config) as inverter:
                inverter.connect()
                inverter_info: InverterInfo = inverter.inv_sock.inverter_info

                if self.main_device is None:
                    self.init_device(inverter=inverter, inverter_info=inverter_info, inverter_model_name=config.inverter_name, verbosity=verbosity)

                    start_time = time.monotonic()
            
                    async def update_sensors():
                        for sensor in self.sensors:
                            sensor.set_state(int(time.monotonic() - start_time))
                            sensor.publish(self.mqtt_client)

                    while True:
                        await update_sensors()
                        await asyncio.sleep(10)
                        
        except ReadTimeout as err:
            print(f'[red]{err}')
        except Exception as err:
            print(f'[red]{err}')
            logger.exception('Unexpected error: %s', err)
                    

            

          
def old_publish_forever(*, config: Config, verbosity):
    start_time = time.monotonic()

    mqtt_settings = config.mqtt_settings
    try:
        publisher = HaMqttPublisher(settings=mqtt_settings, verbosity=verbosity, config_count=1)
    except Exception as err:
        human_error(message='given {mqtt_settings!r} is wrong?!?', exception=err)

    reset_state = DailyProductionResetState(config_path=config.config_path)

    while True:
        try:
            with Inverter(config=config) as inverter:
                inverter.connect()
                inverter_info: InverterInfo = inverter.inv_sock.inverter_info

                with DailyProductionReset(reset_state, inverter, config) as daily_production_reset:

                    try:
                        values = []
                        for value in inverter:
                            assert isinstance(value, InverterValue), f'{value!r}'

                            ha_value = value.value
                            if ha_value == ERROR_STR_NO_DATA:
                                # Don't send a MQTT message if one of the values are missing:
                                raise ReadInverterError(f'Missing data for {value.name}')
                            elif isinstance(value.value, Version):
                                ha_value = str(value.value)

                            daily_production_reset(value)
                            if value.device_class == 'enum':
                                value.state_class = None
                                print(f'[red]{value}')

                            values.append(
                                HaValue(
                                    name=value.name,
                                    value=ha_value,
                                    device_class=value.device_class,
                                    state_class=value.state_class,
                                    unit=value.unit,
                                )
                            )
                    except ValidationError as err:
                        print(f'[red]Skip send values: {err}')
                    except ReadInverterError as err:
                        print(f'[red]{err}')
                    else:
                        values.append(
                            HaValue(
                                name='Loop Running Time',
                                value=int(time.monotonic() - start_time),
                                device_class='',
                                state_class='measurement',
                                unit='sec.',
                            )
                        )

                        values = HaValues(
                            device_name=str(inverter_info.serial),
                            values=values,
                            prefix='homeassistant',
                            component='sensor',
                        )
                        ha_mqtt_payload = values2mqtt_payload(values=values, name_prefix='inverter')
                        publisher.publish2homeassistant(ha_mqtt_payload=ha_mqtt_payload)
        except ReadTimeout as err:
            print(f'[red]{err}')
        except Exception as err:
            print(f'[red]{err}')
            logger.exception('Unexpected error: %s', err)

        print('Wait', end='...')
        for i in range(10, 1, -1):
            time.sleep(1)
            print(i, end='...')
