#!/usr/bin/env python
from ina219 import INA219
from ina219 import DeviceRangeError
import time  # Import time module

SHUNT_OHMS = 0.1

def read():
    ina = INA219(SHUNT_OHMS)
    ina.configure()
    
    while True:
        
        print("Bus Voltage: %.3f V" % ina.voltage())
        try:
            c= ina.current() * 0.45
            print("Bus Current: %.3f mA" % ina.current())
            print("Current:" ,c)
            print("Power: %.3f mW" % ina.power())
            print("Shunt Voltage: %.3f mV" % ina.shunt_voltage())
        except DeviceRangeError as e:
            # Current out of device range with specified shunt resistor
            print(e)

        # Add a delay between readings
        print("---------------------------")
        time.sleep(2)  # Delay for 2 seconds

if __name__ == "__main__":
    read() 
                       
                       
