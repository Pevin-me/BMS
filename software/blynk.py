import time
import smtplib
import board
import busio
import Adafruit_DHT
import blynklib
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from ina219 import INA219, DeviceRangeError

# -----------------------------
# Blynk Configuration
# -----------------------------
BLYNK_AUTH = ""
blynk = blynklib.Blynk(BLYNK_AUTH)

# -----------------------------
# Sensor & Email Configuration
# -----------------------------
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4

SENDER_EMAIL = ""  # your-email@gmail.com
RECEIVER_EMAIL = ""  # recipient-email@gmail.com
EMAIL_PASSWORD = ""  # your app-specific password

TEMP_THRESHOLD = 40.0  # °C

# -----------------------------
# ADS1115 Setup (Battery Voltage)
# -----------------------------
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    print("[INFO] ADS1115 initialized successfully")
except Exception as e:
    print(f"[ERROR] Failed to initialize ADS1115: {e}")
    exit(1)

voltage_channel = AnalogIn(ads, ADS.P0)

# -----------------------------
# INA219 Setup (Load Voltage/Current)
# -----------------------------
SHUNT_OHMS = 0.1
try:
    ina = INA219(SHUNT_OHMS)
    ina.configure()
    print("[INFO] INA219 initialized successfully")
except Exception as e:
    print(f"[ERROR] Failed to initialize INA219: {e}")
    exit(1)

# -----------------------------
# Calibration Constants
# -----------------------------
VOLTAGE_DIVIDER_RATIO = 1.0  # Adjust this if a divider is used
ADS_REF_VOLTAGE = 4.096
ADS_MAX_READING = 32767.0

# -----------------------------
# Utility Functions
# -----------------------------
def read_battery_voltage():
    try:
        adc_voltage = (voltage_channel.value * ADS_REF_VOLTAGE) / ADS_MAX_READING
        battery_voltage = adc_voltage * VOLTAGE_DIVIDER_RATIO
        return battery_voltage * 5  # Multiply if voltage divider used
    except Exception as e:
        print(f"[ERROR] Battery voltage reading failed: {e}")
        return 0.0

def read_load_voltage_current():
    try:
        voltage = ina.voltage()
        current = ina.current() / 1000.0  # Convert mA to A
        return voltage, current
    except DeviceRangeError as e:
        print(f"[ERROR] INA219 out of range: {e}")
        return 0.0, 0.0
    except Exception as e:
        print(f"[ERROR] INA219 read failed: {e}")
        return 0.0, 0.0

def calculate_power(voltage, current):
    return voltage * abs(current)

def send_email_alert(temperature, battery_voltage, load_voltage, current, power):
    subject = "⚠️ BMS Alert: Critical Battery Temperature"
    message = (
        f"Battery Monitoring System Alert\n"
        f"----------------------------------\n"
        f"⚠️ High Temperature Detected!\n\n"
        f"📈 Temperature: {temperature:.1f} °C\n"
        f"🔋 Battery Voltage: {battery_voltage:.2f} V\n"
        f"🔌 Load Voltage: {load_voltage:.2f} V\n"
        f"⚡ Current: {current:.3f} A\n"
        f"⚡ Power: {power:.2f} W\n\n"
        f"Immediate inspection is recommended."
    )
    email_content = f"Subject: {subject}\n\n{message}"

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, email_content)
        print("[INFO] Email alert sent successfully")
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")

# -----------------------------
# Main Execution Loop
# -----------------------------
def main():
    print("=== Battery Monitoring System (BMS) ===")
    print("Monitoring started. Press Ctrl+C to stop.\n")

    try:
        while True:
            blynk.run()

            humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)

            if humidity is not None and temperature is not None:
                battery_voltage = read_battery_voltage()
                load_voltage, current = read_load_voltage_current()
                power = calculate_power(load_voltage, current)

                print(f"[DATA] Temp: {temperature:.1f}°C | Humidity: {humidity:.1f}% | "
                      f"Battery V: {battery_voltage:.2f} V | Load V: {load_voltage:.2f} V | "
                      f"Current: {current:.3f} A | Power: {power:.2f} W")

                # Send data to Blynk
                blynk.virtual_write(0, temperature)        # V0
                blynk.virtual_write(1, humidity)           # V1
                blynk.virtual_write(2, battery_voltage)    # V2
                blynk.virtual_write(3, load_voltage)       # V3
                blynk.virtual_write(4, current)            # V4
                blynk.virtual_write(5, power)              # V5

                if temperature > TEMP_THRESHOLD:
                    send_email_alert(temperature, battery_voltage, load_voltage, current, power)
            else:
                print("[WARN] Failed to retrieve data from DHT22 sensor")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[INFO] BMS monitoring stopped.")

# -----------------------------
# Entry Point
# -----------------------------
if __name__ == "__main__":
    main()
