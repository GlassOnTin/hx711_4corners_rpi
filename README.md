# Raspberry Pi Scale Project

## Overview
This project includes a Python script that interfaces with the HX711 load cell amplifier to create a digital scale using the Raspberry Pi. It's designed to handle multiple sensors, calculate tare and scale factor, and provide bootstrapped confidence intervals for measurements.

Uses: https://pypi.org/project/hx711/

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
- Required Python libraries: `numpy`, `scipy`, `matplotlib`, `RPi.GPIO`, `HX711`

## Installation
1. Clone the repository:
git clone https://github.com/GlassOnTin/hx711_4corners_rpi

2. Install required Python libraries (if not already installed):
pip install numpy scipy matplotlib RPi.GPIO HX711

## Configuration
- The script uses `scale_config.ini` for storing calibration and tare data. Ensure this file is in the same directory as the script or specify the path in the script.

## Usage
```
usage: hx4.py [-h] [-t] [-c CALIBRATE] [-d DURATION] [-n NUMBER] [-o OUTPUT] [-p PLOT] [-H HOST] [-P PORT]

Scale Operation

options:
  -h, --help            show this help message and exit
  -t, --tare            Tare the scale
  -c CALIBRATE, --calibrate CALIBRATE
                        Calibrate the scale with a known weight
  -d DURATION, --duration DURATION
                        Sample duration in seconds
  -n NUMBER, --number NUMBER
                        Number of samples of given duration to report
  -o OUTPUT, --output OUTPUT
                        Path to output results
  -p PLOT, --plot PLOT  Path to output chart of results
  -H HOST, --host HOST  Host address for the HTTP server
  -P PORT, --port PORT  Port for the HTTP server
```

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