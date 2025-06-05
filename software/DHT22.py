import Adafruit_DHT
import time

# Set the sensor type and the GPIO pin
sensor = Adafruit_DHT.DHT22
pin = 4  # Change this if you're using a different GPIO pin

while True:
    # Read the humidity and temperature from the DHT22 sensor
    humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)
    
    # Check if the reading was successful
    if humidity is not None and temperature is not None:
        print(f'Temperature: {temperature:.1f}°C  Humidity: {humidity:.1f}%')
    else:
        print('Failed to get reading. Try again!')
        
    # Wait a short while before the next reading
    time.sleep(2)  # Adjust the interval as needed
