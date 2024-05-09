import dht
from machine import Pin, ADC


class DHT22:
    def __init__(self, pin) -> None:
        self.pin = pin
        self.dht22 = dht.DHT22(Pin(self.pin))

    def measure(self):
        self.dht22.measure()
        try:
            self.temperature = self.dht22.temperature()
        except Exception as e:
            self.temperature = None
            print(e)
        try:
            self.humidity = self.dht22.humidity()
        except Exception as e:
            self.humidity = None
            print(e)
        return (self.dht22.temperature(), self.dht22.humidity())


class SoilSensor:
    def __init__(self, pin) -> None:
        self.pin = pin
        self.soil_sensor = ADC(Pin(pin))
        self.conversion_factor = 65535

    def measure(self):
        try:
            self.value = self.soil_sensor.read_u16()
        except Exception as e:
            self.value = self.conversion_factor
            print(e)

        self.soil_humidity = (1 - self.value / self.conversion_factor) * 100
        return self.soil_humidity


class OnBoardSensor:
    def __init__(self, pin) -> None:
        self.pin = pin
        self.onbaord_sensor = ADC(Pin(pin))
        self.conversion_factor = 3.3 / 65535

    def measure(self):
        try:
            self.value = self.onbaord_sensor.read_u16()
        except Exception as e:
            print(e)
            self.value = 0
        voltage = self.value * self.conversion_factor
        self.onbaord_temp = 27 - (voltage - 0.706) / 0.001721
        return self.onbaord_temp
