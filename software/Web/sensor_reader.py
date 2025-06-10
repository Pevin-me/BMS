import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import Adafruit_DHT
from ina219 import INA219
from ina219 import DeviceRangeError

class BMSSensorReader:
    def __init__(self):
        # Initialize sensors
        self.DHT_SENSOR = Adafruit_DHT.DHT22
        self.DHT_PIN = 4
        self.SHUNT_OHMS = 0.1
        self.VOLTAGE_DIVIDER_RATIO = 1.0
        self.ADS_REF_VOLTAGE = 4.096
        self.ADS_MAX_READING = 32767.0
        
        try:
            # Initialize I2C and ADS1115
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.ads = ADS.ADS1115(self.i2c)
            self.voltage_channel = AnalogIn(self.ads, ADS.P0)
            
            # Initialize INA219
            self.ina = INA219(self.SHUNT_OHMS)
            self.ina.configure()
            
            print("[INFO] All sensors initialized successfully")
        except Exception as e:
            print(f"[ERROR] Sensor initialization failed: {e}")
            raise

    def read_all_sensors(self):
        """Read all sensor values and return as dictionary"""
        data = {
            'temperature': None,
            'humidity': None,
            'battery_voltage': 0.0,
            'load_voltage': 0.0,
            'current': 0.0,
            'power': 0.0,
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            # Read DHT22
            data['humidity'], data['temperature'] = Adafruit_DHT.read_retry(self.DHT_SENSOR, self.DHT_PIN)
            
            # Read battery voltage
            adc_voltage = (self.voltage_channel.value * self.ADS_REF_VOLTAGE) / self.ADS_MAX_READING
            data['battery_voltage'] = adc_voltage * self.VOLTAGE_DIVIDER_RATIO * 5
            
            # Read load voltage and current
            data['load_voltage'] = self.ina.voltage()
            data['current'] = self.ina.current() / 1000.0  # mA to A
            data['power'] = data['load_voltage'] * abs(data['current'])
            
        except Exception as e:
            print(f"[ERROR] Sensor reading failed: {e}")
        
        return data