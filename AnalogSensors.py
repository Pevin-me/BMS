import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# Initialize I2C bus and ADS1115
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    print("ADS1115 initialized successfully")
except Exception as e:
    print(f"Failed to initialize ADS1115: {e}")
    exit(1)

# Create single-ended input channels
voltage_channel = AnalogIn(ads, ADS.P0)  # A0 for voltage sensor
current_channel = AnalogIn(ads, ADS.P1)  # A1 for ACS712 current sensor

# Sensor calibration values (adjust based on your specific setup)
ACS712_SENSITIVITY = 0.06  # 66mV/A for 30A model (ACS712-30A)
ACS712_ZERO_CURRENT_VOLTAGE = 2.47  # Vcc/2 (assuming 5V supply)
VOLTAGE_DIVIDER_RATIO = 1.0  # Adjust based on your voltage divider (if used)
ADS1115_GAIN = 1  # +/-4.096V (default)

def read_voltage():
    """Read and calculate battery voltage"""
    try:
        # Get raw ADC value (0-32767 for ADS1115 in +/-4.096V range)
        adc_value = voltage_channel.value
       
        # Convert to voltage (ADS1115 gain is set to 4.096V by default)
        adc_voltage = (adc_value * 4.096) / 32767.0
       
        # Adjust for voltage divider ratio if used
        battery_voltage = adc_voltage * VOLTAGE_DIVIDER_RATIO
       
        return battery_voltage*5
    except Exception as e:
        print(f"Voltage reading error: {e}")
        return 0.0

def read_current():
    """Read and calculate current using ACS712"""
    try:
        # Get raw ADC value
        adc_value = current_channel.value
       
        # Convert to voltage (ADS1115 gain is set to 4.096V by default)
        sensor_voltage = (adc_value * 4.096) / 32767.0
       
        # Calculate current (subtract zero-current voltage, then divide by sensitivity)
        current = (sensor_voltage - ACS712_ZERO_CURRENT_VOLTAGE) / ACS712_SENSITIVITY
       
        return current
    except Exception as e:
        print(f"Current reading error: {e}")
        return 0.0

def calculate_power(voltage, current):
    """Calculate power in watts"""
    return voltage * abs(current)  # Using abs() to handle negative current readings

def main():
    print("Battery Monitoring System (BMS) - Starting...")
    print("Press Ctrl+C to exit")
   
    try:
        while True:
            # Read sensors
            voltage = read_voltage()
            current = read_current()
            power = calculate_power(voltage, current)
           
            # Print results
            print(f"Voltage: {voltage:.2f} V | Current: {current:.3f} A | Power: {power:.2f} W")
           
            # Wait before next reading
            time.sleep(1)
           
    except KeyboardInterrupt:
        print("\nExiting BMS program")

if __name__ == "__main__":
    main()
