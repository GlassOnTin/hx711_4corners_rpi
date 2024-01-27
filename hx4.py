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
from states import STATE_TARING, STATE_CALIBRATING, STATE_MEASURING

def format_with_precision(value, precision):
    """Format the value with the given precision in decimal places."""
    return f"{value:.{precision}f}"

def calculate_significant_figures(lower_bound, upper_bound):
    """Calculate the number of significant figures (decimal places) for the confidence interval."""
    # Find the decimal places in each bound
    decimal_places_lower = str(lower_bound)[::-1].find('.')
    decimal_places_upper = str(upper_bound)[::-1].find('.')
    # Use the higher number of decimal places
    return max(decimal_places_lower, decimal_places_upper)
    
def signal_handler(sig, frame):
    print('Shutting down the server...')
    httpd.shutdown()  # Shutdown the server
    httpd.server_close()  # Close the server socket
    sys.exit(0)

def main():  
    parser = argparse.ArgumentParser(description="Scale Operation")
    parser.add_argument("-t", "--tare", action="store_true", help="Tare the scale")
    parser.add_argument("-c", "--calibrate", type=float, help="Calibrate the scale with a known weight")
    parser.add_argument("-d", "--duration", type=float, default=10, help="Sample duration in seconds")
    parser.add_argument("-n", "--number", type=int, default=1, help="Number of samples of given duration to report")
    parser.add_argument("-o", "--output", type=str, default="samples.txt", help="Path to output results")
    parser.add_argument("-p", "--plot", type=str, default="samples.png", help="Path to output chart of results")
    parser.add_argument("-H", "--host", type=str, default="localhost", help="Host address for the HTTP server")
    parser.add_argument("-P", "--port", type=int, default=0, help="Port for the HTTP server")

    args = parser.parse_args()
    config = configparser.ConfigParser()
    config_file='scale_config.ini'

    signal.signal(signal.SIGINT, signal_handler)  # Catch CTRL+C and shutdown gracefully
    signal.signal(signal.SIGTERM, signal_handler)  # Catch CTRL+C and shutdown gracefully
    
    if os.path.exists(args.output):
        sample_buffer = deque(np.loadtxt(args.output), maxlen=args.number)
    else:
        sample_buffer = deque(maxlen=args.number)  # Circular buffer for samples

    try:
        scale = Scale()  # Create an instance of Scale
        
        # Create a state queue of maxsize 1
        q = queue.Queue(maxsize=1)
        q.put(STATE_MEASURING)

        if args.port > 0:
            # Pass the scale, current_state, and state_lock to the server
            http_server_thread = threading.Thread(target=start_http_server, args=(args.host, args.port, os.path.dirname(os.path.abspath(__file__)), scale, q))
            http_server_thread.daemon = True
            http_server_thread.start()
            
        if args.tare:
            print("Taring...")
            scale.tare(args.duration)
            print("Taring complete.")

        elif args.calibrate is not None:
            print(f"Calibrating to {args.calibrate}")
            config['DEFAULT']['KnownWeight'] = str(args.calibrate)
            with open(config_file, 'w') as configfile:
                config.write(configfile)
                
            scale.calibrate(args.calibrate, args.duration)
            print("Calibration complete.")

        else:

            while args.number > 1:
                try:
                    state = q.get()
                except Exception as e:
                    pass
        
                if state == STATE_MEASURING:
                    scale.measure(args.duration, sample_buffer, args.output, args.plot)
                    if q.empty():
                        q.put(STATE_MEASURING, block=False)
                    
                elif state == STATE_TARING:
                    # Perform taring and then switch to idle or measuring
                    print("Taring")
                    scale.tare(args.duration)
                    if q.empty():
                        q.put(STATE_MEASURING, block=False)
                    
                elif state == STATE_CALIBRATING:
                    # Perform calibrating and then switch to idle or measuring
                    with open(config_file, 'r') as configfile:
                        config.read(configfile)
                    known_weight = config['DEFAULT']['KnownWeight']
                    print(f"Calibrating to {known_weight}")
                    scale.calibrate(known_weight, args.duration)
                    if q.empty():
                        q.put(STATE_MEASURING, block=False)
                
            
    except Exception as e:
        print(f"An error occurred: {e}")
        traceback.print_exc()
    finally:
        scale.cleanup()
        
if __name__ == "__main__":
    main()
