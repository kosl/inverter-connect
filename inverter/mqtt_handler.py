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
from packaging.version import Version
from rich import print  # noqa

from inverter import __version__
from inverter.api import Inverter
from inverter.connection import InverterSock
from inverter.constants import ERROR_STR_NO_DATA, DEFAULT_DEVICE_MANUFACTURER
from inverter.definitions import get_parameter
from inverter.daily_reset import DailyProductionReset, DailyProductionResetState
from inverter.data_types import Config, InverterInfo, ModbusReadResult
from inverter.exceptions import ReadInverterError, ReadTimeout, ValidationError, ParseModbusValueError, CrcError, ModbusNoData
from inverter.user_settings import UserSettings

logger = logging.getLogger(__name__)

class InverterMqttHandler:
    def __init__(self, config: Config, verbosity: int):
        self.config = config
        self.verbosity = verbosity
        self.mqtt_client = get_connected_client(settings=config.mqtt_settings, verbosity=verbosity)
        self.mqtt_client.loop_start()
        self.main_device: MqttDevice|None = None
        self.parameters = get_parameter(config=config)
        self.sensors = list()
        self.sensor_loop_running_time = None

    def init_device(self, inverter_info: InverterInfo, verbosity: int):
        """
        Create sensors from definitions/*.yaml add it to device for later
        update in publish process.
        """
        self.main_device = MqttDevice(
            name=DEFAULT_DEVICE_MANUFACTURER+' '+str(inverter_info.serial),
            uid='inverter_'+str(inverter_info.serial), # Required for multiple inverters to appear as main device
            manufacturer=DEFAULT_DEVICE_MANUFACTURER,
            model=self.config.inverter_name.upper(),
            sw_version=__version__,
            config_throttle_sec=self.config.mqtt_settings.publish_config_throttle_seconds,
        )
        self.sensor_loop_running_time = Sensor(
            device=self.main_device,
            name='Loop Running Time',
            uid=slugify('Loop Running Time'),
            device_class=None,
            state_class='measurement',
            unit_of_measurement='sec.',
            suggested_display_precision=0,
        )

        for parameter in self.parameters:
            self.sensors.append((Sensor(
                device=self.main_device,
                name=parameter.name,
                uid=slugify(parameter.name),
                device_class=parameter.device_class,
                state_class=parameter.state_class,
                unit_of_measurement=parameter.unit_of_measurement,
                suggested_display_precision=len(str(parameter.scale)[str(parameter.scale).rfind('.')+1:]) if parameter.scale < 1 else 0
            ), parameter))
        
        
    def publish_loop(self, verbosity):
        try:
            if self.main_device is None:
                with InverterSock(config=self.config) as inverter_socket:
                    inverter_socket.connect()
                    inverter_info: InverterInfo = inverter_socket.inverter_info
                    self.init_device(inverter_info, verbosity)

            start_time = time.monotonic()
            
            print("[blue]Starting publishing loop...")
            while True:
                with InverterSock(config=self.config) as inverter_socket:
                        inverter_socket.connect()
                        self.sensor_loop_running_time.set_state(int(time.monotonic() - start_time))
                        self.sensor_loop_running_time.publish(self.mqtt_client)
                        for sensor, parameter in self.sensors:
                            try:
                                result: ModbusReadResult = inverter_socket.read_parameter(parameter=parameter)
                            except (ParseModbusValueError, CrcError, ModbusNoData) as err:
                                print(f'[red]Skipping "{parameter.name}" update due to {err}')
                            else:
                                sensor.set_state(result.parsed_value)
                                sensor.publish(self.mqtt_client)
                time.sleep(10)
                        
        except ReadTimeout as err:
            print(f'[red]{err}')
        except Exception as err:
            print(f'[red]{err}')
            logger.exception('Unexpected error: %s', err)
                    

            

          
def old_publish_forever(*, config: Config, verbosity): # 
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
                                    unit_of_measurement=value.unit,
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
                                unit_of_measurement='sec.',
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
