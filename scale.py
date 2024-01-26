import configparser
import time
import numpy as np
import RPi.GPIO as GPIO
from hx711 import HX711


class Scale:
    def __init__(self, config_file='scale_config.ini'):
        self.sensors = [
            self.initialize_sensor(5, 6),
            self.initialize_sensor(17, 18),
            self.initialize_sensor(19, 20),
            self.initialize_sensor(23, 22)
        ]
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.config.read(self.config_file)

    def initialize_sensor(self, dout_pin, pd_sck_pin):
        sensor = HX711(dout_pin=dout_pin, pd_sck_pin=pd_sck_pin)
        sensor.min_measures = 1
        sensor.reset()
        return sensor

    def collect_sample(self):
        readings = [sensor.get_raw_data(times=1)[0] for sensor in self.sensors]
        return sum(readings)

    def collect_samples(self, duration):
        end_time = time.time() + duration
        samples = []
        while time.time() < end_time:
            samples.append(self.collect_sample())
        return np.array(samples)

    def tare(self, duration):
        print("Taring the scale. Ensure the scale is empty.")
        tare_value = np.median(self.collect_samples(duration))
        self.config['DEFAULT']['TareValue'] = str(tare_value)
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)
        return tare_value

    def calibrate(self, known_weight, duration):
        print(f"Place a known weight of {known_weight} units on the scale.")
        tare_value = float(self.config['DEFAULT']['TareValue'])
        reading_with_weight = np.median(self.collect_samples(duration))
        scale_factor = known_weight / (reading_with_weight - tare_value)
        self.config['DEFAULT']['ScaleFactor'] = str(scale_factor)
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)
        return scale_factor
        
    def weight_from_raw(self, sample):
        if 'ScaleFactor' not in self.config['DEFAULT'] or 'TareValue' not in self.config['DEFAULT']:
            print("Error: Scale must be calibrated and tared before collecting samples.")
            print("Please run calibration with '-c <weight>' and taring with '-t'.")
            return

        scale_factor = float(self.config['DEFAULT']['ScaleFactor'])
        tare_value = float(self.config['DEFAULT']['TareValue'])
        return (sample - tare_value) * scale_factor

        
    def bootstrap_confidence_interval(self, data, n_bootstraps=1000, ci=95):
        bootstrapped_samples = np.random.choice(data, (n_bootstraps, len(data)), replace=True)
        bootstrapped_medians = np.median(bootstrapped_samples, axis=1)
        lower_bound = np.percentile(bootstrapped_medians, (100 - ci) / 2)
        upper_bound = np.percentile(bootstrapped_medians, 100 - (100 - ci) / 2)
        return lower_bound, upper_bound
        
    def cleanup(self):
        GPIO.cleanup()
