# Raspberry Pi Scale Project

## Overview

This project develops a digital scale using the Raspberry Pi, interfacing with the HX711 load cell amplifier. Designed to support multiple sensors, it enables users to tare the scale, calibrate with known weights, and collect sample data over specified durations. Additionally, it calculates bootstrapped confidence intervals for the measurements, enhancing the reliability of the data collected.

**Uses** : [HX711 Python Library on PyPI](https://pypi.org/project/hx711/) 

## Features
- Simple Web interface with live chart
- Multi-sensor support with HX711 load cell amplifiers.
- Taring functionality for zeroing the scale.
- Calibration capability using a known weight.
- Data collection over a user-defined duration.
- Bootstrapped confidence interval calculations for precision measurement analysis.

![Screenshot](https://raw.githubusercontent.com/GlassOnTin/hx711_4corners_rpi/main/Screenshot.png)

## Requirements 
- **Hardware** : Raspberry Pi (Tested on Raspberry Pi 4), HX711 load cell amplifier, compatible load cells. 
- **Software** : Python 3.x and required Python libraries: `numpy`, `scipy`, `matplotlib`, `RPi.GPIO`, `HX711`.

## Installation 
1. **Clone the Repository** :

```bash
git clone https://github.com/GlassOnTin/hx711_4corners_rpi
``` 
2. **Install Required Python Libraries** :

```Copy code
pip install numpy scipy matplotlib RPi.GPIO HX711
```

## Configuration

The script relies on a configuration file (`scale_config.ini`) to store calibration data, tare values, and other settings. This file should be located in the same directory as the script. The configuration can be specified as follows:

```ini
[DEFAULT]
knownweight = 569.0
tare_value = 1974271.5
scale_factor = 0.0012627829559136343
tare = False
calibrate = None
duration = 10.0
number = 10000
output = samples.txt
plot = samples.png
host = 0.0.0.0
port = 7999
```

## Usage

Execute the script with the following command line options to perform scale operations:

```lua
usage: hx4.py [-h] [-t] [-c CALIBRATE] [-d DURATION] [-n NUMBER] [-o OUTPUT] [-p PLOT] [-H HOST] [-P PORT]

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

### Calibration and Taring 
- **Calibration** : Utilize the `--calibrate` option with a known weight to calibrate the scale. 
- **Taring** : Use the `--tare` option to zero the scale before measurements.

### Example Commands 
- Collect samples for 60 seconds: `python hx4.py -d 60` 
- Bind HTTP server to all interfaces: `python hx4.py -H 0.0.0.0 -P 7999` 
- Set the circular buffer length: `python hx4.py -n 10000`

## License
This project is licensed under the MIT License. For more details, see the [LICENSE.md](https://chat.openai.com/c/LICENSE.md)  file.---
