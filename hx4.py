#!/usr/bin/python3
import argparse
import configparser
import os
import signal
import traceback

from collections import deque
import numpy as np

import urllib
from urllib.parse import urlparse
import http.server
import socket
import socketserver
import threading
import queue

from scale import Scale
from http_server import start_http_server  # Import the server start function
from states import STATE_TARING, STATE_CALIBRATING, STATE_MEASURING, STATE_CLEARING

def safe_getfloat(config, section, option, fallback):
    """Safely get a float value from the config, providing a fallback if necessary."""
    try:
        return config.getfloat(section, option)
    except (configparser.NoSectionError, configparser.NoOptionError):
        return fallback

def load_config_and_parse_args():
    config = configparser.ConfigParser()
    config_file = 'scale_config.ini'
    config.read(config_file)  # Load the configuration file
    
    # Ensure defaults are set for scale_factor and tare_value
    if 'scale_factor' not in config['DEFAULT'] or not config['DEFAULT']['scale_factor'].replace('.', '', 1).isdigit():
        config['DEFAULT']['scale_factor'] = '1'  # Default value
    
    if 'tare_value' not in config['DEFAULT'] or not config['DEFAULT']['tare_value'].replace('.', '', 1).lstrip('-').isdigit():
        config['DEFAULT']['tare_value'] = '0'  # Default value

    # Define command-line arguments with defaults from the configuration file
    parser = argparse.ArgumentParser(description="Scale Operation")
    parser.add_argument("-t", "--tare", nargs='?', type=float, const=safe_getfloat(config, 'DEFAULT', 'tare_weight', 0.0), default=np.inf, help="Tare the scale to the specified weight. If no weight is provided, default to 0.0")
    parser.add_argument("-c", "--calibrate", type=float, help="Calibrate the scale with a known weight")
    parser.add_argument("-d", "--duration", type=float, default=safe_getfloat(config, 'DEFAULT', 'duration', 1.0), help="Sample duration in seconds")
    parser.add_argument("-n", "--number", type=int, default=config.getint('DEFAULT', 'number', fallback=1), help="Number of samples of given duration to report")
    parser.add_argument("-o", "--output", type=str, default=config.get('DEFAULT', 'output', fallback='samples.txt'), help="Path to output results")
    parser.add_argument("-p", "--plot", type=str, default=config.get('DEFAULT', 'plot', fallback='samples.png'), help="Path to output chart of results")
    parser.add_argument("-H", "--host", type=str, default=config.get('DEFAULT', 'host', fallback='localhost'), help="Host address for the HTTP server")
    parser.add_argument("-P", "--port", type=int, default=config.getint('DEFAULT', 'port', fallback=0), help="Port for the HTTP server")
    parser.add_argument("--density", type=float, default=safe_getfloat(config, 'DEFAULT', 'density_gcm3', 1.07), help="The material density in g/cm^3, used to estimate remaining material length")
    parser.add_argument("--diameter", type=float, default=safe_getfloat(config, 'DEFAULT', 'diameter_mm', 1.75), help="The material diameter in mm, used to estimate remaining material length")

    args = parser.parse_args()

    if args.tare != np.inf:
        print(f"Taring the scale to {args.tare}g.")
    else:
        print("No taring requested.")
    
    # Map from command line argument names to config names
    cli_to_config_map = {
        'tare': 'tare_weight',
        'calibrate': 'target_weight',
        'density': 'density_gcm3',
        'diameter': 'diameter_mm'
    }

    # Update the config file if any argument is provided
    args_dict = vars(args)
    for cli_arg, config_name in cli_to_config_map.items():
        if args_dict.get(cli_arg) is not None:
            config['DEFAULT'][config_name] = str(args_dict[cli_arg])

    # Directly map arguments without name changes
    for arg in args_dict:
        if arg not in cli_to_config_map and args_dict[arg] is not None:
            config['DEFAULT'][arg] = str(args_dict[arg])

    # Save updates to config file
    with open(config_file, 'w') as configfile:
        config.write(configfile)

    return args, config

def state_machine(state_queue, args, config_file):
    scale = Scale()
    
    try:
        while True:
            config = configparser.ConfigParser()
            config.read(config_file)  # Reload the configuration on each iteration
            duration = safe_getfloat(config, 'DEFAULT', 'duration', 1.0)
            tare_weight = safe_getfloat(config, 'DEFAULT', 'tare_weight', 0.0)
            tare_value = safe_getfloat(config, 'DEFAULT', 'tare_value', 0.0)
            target_weight = safe_getfloat(config, 'DEFAULT', 'target_weight', 1000.0)
            scale_factor = safe_getfloat(config, 'DEFAULT', 'scale_factor', 1.0)
            buffer_length = int(config['DEFAULT']['number'])
            sample_file = config['DEFAULT']['output']
            plot_file = config['DEFAULT']['plot']
            density_gcm3 = safe_getfloat(config, 'DEFAULT', 'density_gcm3', 1.07)
            diameter = safe_getfloat(config, 'DEFAULT', 'diameter_mm', 1.75)            
            
            try:
                state = state_queue.get_nowait()
            except queue.Empty:
                state = STATE_MEASURING  # Default state if the queue is empty

            if state == STATE_MEASURING:               
                time_array, sample_buffer, smoothed_data = scale.measure(
                    duration, 
                    scale_factor, 
                    tare_value, 
                    sample_file, 
                    buffer_length)
                    
                scale.plot(time_array, sample_buffer, smoothed_data, plot_file)
                
                time_to_zero_timedelta, estimated_zero_datetime = scale.estime_time_to_zero( duration, smoothed_data)        
                                                           
            elif state == STATE_TARING:
                print("Taring...")
                tare_value = scale.tare(duration)
                
                config['DEFAULT']['tare_value'] = tare_value
                with open(config_file, 'w') as configfile:
                    config.write(configfile)
                print("Taring complete.")                
                
            elif state == STATE_CALIBRATING:
                print(f"Calibrating to {target_weight}")
                
                config['DEFAULT']['scale_factor'] = scale.calibrate(target_weight, duration)
                with open(config_file, 'w') as configfile:
                    config.write(configfile)

                print("Calibration complete.")
                
            elif state == STATE_CLEARING:
                print("Clearing...")
                sample_file = config['DEFAULT']['output']
                if os.path.exists(sample_file):
                    os.remove(sample_file)
                print("Clearing complete")

    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()

    finally:
        scale.cleanup()
   
def signal_handler(sig, frame):
    print('Shutting down the server...')
    httpd.shutdown()  # Shutdown the server
    httpd.server_close()  # Close the server socket
    sys.exit(0)

def main():  
    signal.signal(signal.SIGINT, signal_handler)  # Catch CTRL+C and shutdown gracefully
    signal.signal(signal.SIGTERM, signal_handler)  # Catch CTRL+C and shutdown gracefully
        
    args, config = load_config_and_parse_args()
    
    # Pass the scale, current_state, and state_lock to the server
    host = config['DEFAULT']['host']
    port = int(config['DEFAULT']['port'])
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    
    state_queue = queue.Queue(maxsize=1)
    
    http_server_thread = threading.Thread(target=start_http_server, args=(host, port, cur_dir, state_queue))
    http_server_thread.daemon = True
    http_server_thread.start()
    
    state_machine(state_queue, args, 'scale_config.ini')
        
if __name__ == "__main__":
    main()
