import os
import time
import numpy as np
import RPi.GPIO as GPIO
from hx711 import HX711

from collections import deque
import numpy as np
from scipy.signal import filtfilt, butter

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from scipy.optimize import root_scalar

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

    def collect_samples(self, sample_duration):
        end_time = time.time() + sample_duration
        samples = []
        while time.time() < end_time:
            samples.append(self.collect_sample())
        return np.array(samples)

    def tare(self, sample_duration):
        print("Taring the scale. Ensure the scale is empty.")
        tare_value = np.median(self.collect_samples(sample_duration))
        return tare_value

    def calibrate(self, known_weight, sample_duration):
        print(f"Place a known weight of {known_weight} units on the scale.")
        reading_with_weight = np.median(self.collect_samples(sample_duration))
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
          
    def measure(self, sample_duration=10, scale_factor=1, tare_value=0, sample_file="samples.txt", buffer_length=10000, plot_file="samples.png"):
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

        samples = self.collect_samples(sample_duration)
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
            
        # Saving the plot if a filename is provided
        if plot_file is not None:
            # Calculate the time interval between samples
            total_samples = len(sample_buffer)

            # Create a time array that corresponds to each sample
            time_array = np.linspace(0, sample_duration*total_samples/60, total_samples)
            
            def butter_lowpass_filter(data, cutoff_freq, fs, order=3):
                nyq = 0.5 * fs  # Nyquist Frequency
                normal_cutoff = cutoff_freq / nyq
                # Get the filter coefficients 
                b, a = butter(order, normal_cutoff, btype='low', analog=False)
                y = filtfilt(b, a, data)
                return y

            # Example usage
            fs = 1.0 / sample_duration  # Sampling frequency in min^-1
            cutoff_freq = 1.0/(5.0*60)  # Cutoff frequency in min^-1 
            smoothed_data = butter_lowpass_filter(np.array(sample_buffer), cutoff_freq, fs)
            
            # Use the original time_array for plotting since we've adjusted smoothed_data to match its length
            plt.figure(figsize=(10, 6))
            plt.scatter(time_array, sample_buffer, label='Raw Weight (g)', alpha=0.5, s=10, color='gray')  # Plot raw data as dots
            plt.plot(time_array, smoothed_data, label='Smoothed Weight (g)', color='blue')  # Plot smoothed (and padded) data as a line
            plt.xlabel('Time (min)')
            plt.ylabel('Weight (g)')
            plt.title('Weight Measurement Over Time')
            plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True, nbins=10))
            plt.legend()
            plt.show()
            
            tmp_file = plot_file + ".tmp.png"
            plt.savefig(tmp_file)
            plt.close()

            # Rename the temporary file to the final filename, ensuring overwrite
            if os.path.exists(plot_file):
                os.remove(plot_file)
            os.rename(tmp_file, plot_file)
            

    def cleanup(self):
        GPIO.cleanup()
