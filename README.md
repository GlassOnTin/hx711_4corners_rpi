# Raspberry Pi Scale Project

## Overview
This project includes a Python script that interfaces with the HX711 load cell amplifier to create a digital scale using the Raspberry Pi. It's designed to handle multiple sensors, calculate tare and scale factor, and provide bootstrapped confidence intervals for measurements.

## Features
- Support for multiple HX711 sensors.
- Functions to tare the scale and calibrate with a known weight.
- Ability to collect sample data over a set duration.
- Calculation of bootstrapped confidence intervals for collected data.

## Requirements
- Raspberry Pi (Tested on Raspberry Pi 4).
- HX711 load cell amplifier.
- Compatible load cells.
- Python 3.x
- Required Python libraries: `numpy`, `RPi.GPIO`.

## Installation
1. Clone the repository:
git clone [URL of your repository]

2. Install required Python libraries (if not already installed):
pip install numpy scipy matplotlib RPi.GPIO HX711

markdown
Copy code

## Configuration
- The script uses `scale_config.ini` for storing calibration and tare data. Ensure this file is in the same directory as the script or specify the path in the script.

## Usage
- To use the script, run `python hx4.py` with the following command line options:
- `-d [duration]`: Set the duration for collecting samples.
- `-H [host]`: Set the host for the service (default is `0.0.0.0`).
- `-P [port]`: Set the port for the service (default is `7999`).
- `-n [number]`: Set the number of measurements (default is `10000`).

- Calibration and taring can be performed through the script's methods.

## Calibration and Taring
- To calibrate the scale, use the `calibrate` method with a known weight.
- To tare the scale, use the `tare` method.

## Command Line Options
- The `hx4.py` script supports the following command line arguments:
-d 60 # Collect samples for 60 seconds
-H 0.0.0.0 # Host IP address to bind to (for network-based operations)
-P 7999 # Port number for the service
-n 10000 # Length of the circular buffer of measurement

## License
This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for d