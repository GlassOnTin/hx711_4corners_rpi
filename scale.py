import os
import time
import numpy as np
import RPi.GPIO as GPIO
from hx711 import HX711

from collections import deque
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

class Scale:
    def __init__(self):
        self.sensors = [
            self.initialize_sensor(5, 6),
            self.initialize_sensor(17, 18),
            self.initialize_sensor(19, 20),
            self.initialize_sensor(23, 22)
        ]

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
        return tare_value

    def calibrate(self, known_weight, duration):
        print(f"Place a known weight of {known_weight} units on the scale.")
        reading_with_weight = np.median(self.collect_samples(duration))
        scale_factor = known_weight / (reading_with_weight - tare_value)
        return scale_factor
        
    def weight_from_raw(self, samples, scale_factor, tare_value):
        return (samples - tare_value) * scale_factor
        
    def bootstrap_confidence_interval(self, data, n_bootstraps=1000, ci=95):
        bootstrapped_samples = np.random.choice(data, (n_bootstraps, len(data)), replace=True)
        bootstrapped_medians = np.median(bootstrapped_samples, axis=1)
        lower_bound = np.percentile(bootstrapped_medians, (100 - ci) / 2)
        upper_bound = np.percentile(bootstrapped_medians, 100 - (100 - ci) / 2)
        return lower_bound, upper_bound
          
    def measure(self, duration=10, scale_factor=1, tare_value=0, sample_file="samples.txt", buffer_length=10000, plot_file="samples.png"):
        # Check if the file exists and is not empty
        if os.path.exists(sample_file) and os.path.getsize(sample_file) > 0:
            try:
                # Load the file content
                file_buffer = np.loadtxt(sample_file, ndmin=1)  # Ensure at least 1D array is returned
                sample_buffer = deque(file_buffer, maxlen=buffer_length)
            except Exception as e:
                print(e)
                sample_buffer = deque(maxlen=buffer_length)  # Circular buffer for samples
        else:
            sample_buffer = deque(maxlen=buffer_length)  # Initialize an empty buffer if file doesn't exist or is empty

        samples = self.collect_samples(duration)
        samples = self.weight_from_raw(samples, scale_factor, tare_value)
        median_value = np.median(samples)
        lower_bound, upper_bound = self.bootstrap_confidence_interval(samples)
        ci_range = upper_bound - lower_bound
        significant_figures = int(-np.floor(np.log10(ci_range)))
        significant_figures = max(1,significant_figures)
        formatted_median = float(f"{median_value:.{significant_figures}f}")
        formatted_range = float(f"{ci_range:.{significant_figures}f}")
        sample_buffer.append(formatted_median)

        # Output the result
        print(f"{formatted_median} {formatted_range}", flush=True)

        # Append the result to the circular buffer and save to file
        if sample_file != None:
            # When saving, ensure the data is in an array format, especially if it's a single value
            np.savetxt(sample_file, list(sample_buffer))
            
        if plot_file != None:
            # Create a line plot
            plt.figure(figsize=(10, 6))  # You can adjust the size of the plot
            plt.plot(sample_buffer, label='Weight (g)')
            plt.xlabel('Sample Number')
            plt.ylabel('Weight (g)')
            plt.title('Weight (g)')
            
            # Ensure axes have only integer values and control the tick density
            plt.gca().xaxis.set_major_locator(MaxNLocator(integer=True, nbins=10))
            plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True, nbins=10))  

            # Save the plot to a PNG file
            plt.savefig(plot_file)
            plt.close()

    def cleanup(self):
        GPIO.cleanup()
