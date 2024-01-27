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

def safe_getfloat(config, section, option, fallback=None):
    try:
        # Attempt to get the value and convert it to float
        value_str = config.get(section, option, fallback=str(fallback))
        return float(value_str) if value_str.lower() != 'none' else fallback
    except ValueError:
        # Handle the case where conversion to float fails
        return fallback
        
def load_config_and_parse_args():
    config = configparser.ConfigParser()
    config_file = 'scale_config.ini'
    config.read(config_file)  # Load the configuration file
    
    # Check and set default for scale_factor
    if 'scale_factor' not in config['DEFAULT'] or not config['DEFAULT']['scale_factor'].replace('.', '', 1).isdigit():
        config['DEFAULT']['scale_factor'] = '1'  # Default value
    
    # Check and set default for tare_value
    if 'tare_value' not in config['DEFAULT'] or not config['DEFAULT']['tare_value'].replace('.', '', 1).lstrip('-').isdigit():
        config['DEFAULT']['tare_value'] = '0'  # Default value

    # Define command-line arguments with defaults from the configuration file
    parser = argparse.ArgumentParser(description="Scale Operation")
    parser.add_argument("-t", "--tare", action="store_true", default=config.getboolean('DEFAULT', 'Tare', fallback=False), help="Tare the scale")
    parser.add_argument("-c", "--calibrate", type=float, default=safe_getfloat(config,'DEFAULT', 'Calibrate', fallback=None), help="Calibrate the scale with a known weight")
    parser.add_argument("-d", "--duration", type=float, default=safe_getfloat(config,'DEFAULT', 'Duration', fallback=10), help="Sample duration in seconds")
    parser.add_argument("-n", "--number", type=int, default=config.getint('DEFAULT', 'Number', fallback=1), help="Number of samples of given duration to report")
    parser.add_argument("-o", "--output", type=str, default=config.get('DEFAULT', 'Output', fallback='samples.txt'), help="Path to output results")
    parser.add_argument("-p", "--plot", type=str, default=config.get('DEFAULT', 'Plot', fallback='samples.png'), help="Path to output chart of results")
    parser.add_argument("-H", "--host", type=str, default=config.get('DEFAULT', 'Host', fallback='localhost'), help="Host address for the HTTP server")
    parser.add_argument("-P", "--port", type=int, default=config.getint('DEFAULT', 'Port', fallback=0), help="Port for the HTTP server")
    args = parser.parse_args()

    # Update the config file if any argument is provided
    with open(config_file, 'w') as configfile:
        config['DEFAULT'].update({arg: str(getattr(args, arg)) for arg in vars(args)})
        config.write(configfile)

    return args, config

def state_machine(state_queue, args, config_file):
    scale = Scale()
    
    try:
        while True:
            config = configparser.ConfigParser()
            config.read(config_file)  # Reload the configuration on each iteration
            duration = config['DEFAULT']['duration']
            
            try:
                state = state_queue.get_nowait()
            except queue.Empty:
                state = STATE_MEASURING  # Default state if the queue is empty

            if state == STATE_MEASURING:
                tare_value = float(config['DEFAULT']['tare_value'])
                scale_factor = float(config['DEFAULT']['scale_factor'])
                buffer_length = int(config['DEFAULT']['number'])
                sample_file = config['DEFAULT']['output']
                plot_file = config['DEFAULT']['plot']
                scale.measure(args.duration, scale_factor, tare_value, sample_file, buffer_length, plot_file)
                                           
            elif state == STATE_TARING:
                print("Taring...")
                config['DEFAULT']['tare_value'] = scale.tare(args.duration)
                with open(config_file, 'w') as configfile:
                    config.write(configfile)
                print("Taring complete.")                
                
            elif state == STATE_CALIBRATING:
                target_weight = config['DEFAULT']['calibrate']             
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
