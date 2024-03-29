import os
import time
import datetime
import traceback
import numpy as np
import RPi.GPIO as GPIO
from hx711 import HX711

from collections import deque
import numpy as np
from scipy.signal import wiener, medfilt

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from scipy.optimize import root_scalar
from concurrent.futures import ThreadPoolExecutor

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

    def get_sensor_data(self, sensor):
        return sensor.get_raw_data(times=1)[0]

    def collect_sample(self):
        with ThreadPoolExecutor() as executor:
            # Schedule the get_sensor_data function to be called on each sensor
            futures = [executor.submit(self.get_sensor_data, sensor) for sensor in self.sensors]
            # Collect results as they are completed
            readings = [future.result() for future in futures]
        return sum(readings)

    #def collect_sample(self):
    #    readings = [sensor.get_raw_data(times=1)[0] for sensor in self.sensors]
    #    return sum(readings)

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
    
    def filter_data(self, data, window):
        # Ensure the window size is odd
        if window % 2 == 0:
            window = window + 1
        
        for i in range(3):
            # Apply initial filter
            if window > 1:
                data_filtered = medfilt(data, window)
            else:
                data_filtered = data                
        
            # Identify and remove outliers
            delta = np.abs(data_filtered - data)
            sigma = np.std(delta)
            outliers = delta < 3*sigma
            data_cleaned = np.array(data)
            data_cleaned[outliers] = data_filtered[outliers]
            
            # Reapply Wiener filter on cleaned data
            if len(data_cleaned) > window:
                data_final_filtered = wiener(data_cleaned, window)
            else:
                data_final_filtered = data
                
            data = np.array(data_filtered)
            data_filtered = np.array(data_final_filtered)
        
        return data_final_filtered, sigma
          
    def measure(self, 
        sample_duration=10, 
        scale_factor=1, 
        tare_value=0, 
        sample_file="samples.txt", 
        buffer_length=10000, 
        low_pass_minutes=10 ):
        
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
        sigma = upper_bound - lower_bound
        significant_figures = int(-np.floor(np.log10(sigma)))
        significant_figures = max(1,significant_figures)
        formatted_median = float(f"{median_value:.{significant_figures}f}")
        formatted_range = float(f"{sigma:.{significant_figures}f}")
        sample_buffer.append(formatted_median)

        # Append the result to the circular buffer and save to file
        if sample_file != None:
            # When saving, ensure the data is in an array format, especially if it's a single value
            np.savetxt(sample_file, list(sample_buffer))
        
        # Create a time array that corresponds to each sample
        total_samples = len(sample_buffer)
        time_array = np.linspace(0, sample_duration*total_samples/60, total_samples)
        
        # Filter the data to reduce noise
        try:
            b = np.array(sample_buffer)

            window = int(low_pass_minutes * 60 / sample_duration)
            if window>5 and len(sample_buffer)>window:
                window = int(len(sample_buffer) / 2)
            else:
                print(f"window={window}<=5 or len(sample_buffer)={len(sample_buffer)}<={window}")
                return time_array, sample_buffer, b

            # Ensure the window size is odd
            if window % 2 == 0:
                window = window + 1
                
            # Correctly reflect and append data at both ends
            # Reflect the start of the array and append to the beginning
            start_reflection = 2.0*b[0] - b[:window][::-1]
            # Reflect the end of the array and append to the end
            end_reflection = 2.0*b[-1] - b[-window:][::-1]

            # Combine start reflection, original array, and end reflection
            b_reflected = np.concatenate([start_reflection, b, end_reflection])

            # Apply Wiener filter
            b_filtered, sigma = self.filter_data(b_reflected, window)

            # Remove the reflected parts to get the smoothed data of original length
            smoothed_data = b_filtered[window:-window]

        except Exception as e:
            print("Exception in Scale.plot", e)
            traceback.print_exc()
            smoothed_data = np.array(sample_buffer)

        # Output the result
        formatted_range = float(f"{sigma:.{significant_figures}f}")
        print(f"{formatted_median} {formatted_range}", flush=True)
                
        return time_array, sample_buffer, smoothed_data
        
    def plot(self, time_array, sample_buffer, smoothed_data, plot_file="samples.png", density_gcm3 = 1.07, diameter_mm = 1.75):
        # Saving the plot if a filename is provided
        if plot_file is None:
            return
        if sample_buffer is None or len(sample_buffer) <= 1:
            return 
        if smoothed_data is None or len(smoothed_data) <= 1:
            return
            
        try:
            # Calculate a margin for the y-axis range for better visualization
            margin = (smoothed_data.max() - smoothed_data.min()) * 0.05  # 5% margin            

            # Constants for ASA filament
            radius_cm = diameter_mm / 2.0 / 10.0  # Convert mm to cm
            volume_per_cm = np.pi * radius_cm**2  # Volume per cm of filament

            # Calculate weight to length conversion (cm per g)
            length_per_g = 1 / (volume_per_cm * density_gcm3)

            # Convert smoothed weight data to length (assuming weight is in grams)
            smoothed_length = smoothed_data * length_per_g / 100.0  # Convert cm to meters

            # Use the original time_array for plotting since we've adjusted smoothed_data to match its length
            plt.figure(figsize=(10, 6))
            plt.scatter(time_array, sample_buffer, label='Raw Weight (g)', alpha=0.9, s=10, color='gray')  # Plot raw data as dots
            plt.plot(time_array, smoothed_data, label='Smoothed Weight (g)', color='blue')  # Plot smoothed (and padded) data as a line
            plt.xlabel('Time (min)')
            plt.ylabel('Weight (g)')
            plt.title('Weight Measurement Over Time')
            plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True, nbins=10))
            plt.ylim(smoothed_data.min() - margin, smoothed_data.max() + margin)

            # Create secondary y-axis (length)
            ax2 = plt.gca().twinx()
            ax2.plot(time_array, smoothed_length, label='Filament Length (m)', color='blue')
            ax2.set_ylabel('Length (m)')
            ax2.yaxis.set_major_locator(MaxNLocator(nbins=10))

            plt.show()

            tmp_file = plot_file + ".tmp.png"
            plt.savefig(tmp_file)
            plt.close()

            # Rename the temporary file to the final filename, ensuring overwrite
            if os.path.exists(plot_file):
                os.remove(plot_file)
            os.rename(tmp_file, plot_file)

        except Exception as e:
            print("Exception in Scale.plot", e)
            traceback.print_exc()
        
    def estime_time_to_zero(self, sample_duration, smoothed_data):
        try:
            # Estimate the time until zero
            # Calculate gradients between consecutive points
            gradients = np.diff(smoothed_data) / sample_duration  # Assuming time_array is in minutes
            median_gradient = np.median(gradients)

            if median_gradient >= 0 and median_gradient==np.inf and not median_gradient==np.nan:
                time_to_zero = -smoothed_data[-1] / median_gradient
            else:
                time_to_zero = 0
                
            time_to_zero_timedelta = datetime.timedelta(minutes=time_to_zero)
            estimated_zero_datetime = datetime.datetime.now() + time_to_zero_timedelta

            return time_to_zero_timedelta, estimated_zero_datetime

        except Exception as e:
            print("Exception in Scale.plot", e)
            traceback.print_exc()
        
            return np.inf, datetime.datetime.now()
            
    def cleanup(self):
        GPIO.cleanup()
