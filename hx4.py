#!/usr/bin/python3
import argparse
import os
from collections import deque
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import http.server
import socketserver
import threading

from scale import Scale

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
    
class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        http.server.SimpleHTTPRequestHandler.end_headers(self)

    def do_GET(self):
        if self.path.endswith(".png") or self.path.endswith(".txt"):
            return http.server.SimpleHTTPRequestHandler.do_GET(self)
        else:
            self.send_error(404, "File Not Found: %s" % self.path)

def start_http_server(host, port, directory):
    with socketserver.TCPServer((host, port), CustomHandler) as httpd:
        print(f"Serving at http://{host}:{port}")
        os.chdir(directory)  # Change working directory to serve files
        httpd.serve_forever()


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

    scale = Scale()

    try:
        if args.port>0:
            # Start the HTTP server in a separate thread
            http_server_thread = threading.Thread(target=start_http_server, args=(args.host, args.port, os.path.dirname(os.path.abspath(__file__))))
            http_server_thread.daemon = True
            http_server_thread.start()

        if args.tare:
            scale.tare(args.duration)
            print("Taring complete.")
        elif args.calibrate is not None:
            scale.calibrate(args.calibrate, args.duration)
            print("Calibration complete.")
        else:
            if os.path.exists(args.output):
                sample_buffer = deque(np.loadtxt(args.output), maxlen=args.number)
            else:
                sample_buffer = deque(maxlen=args.number)  # Circular buffer for samples

            
            while args.number > 1:
                samples = scale.collect_samples(args.duration)
                samples = scale.weight_from_raw(samples)
                median_value = np.median(samples)
                lower_bound, upper_bound = scale.bootstrap_confidence_interval(samples)
                ci_range = upper_bound - lower_bound
                significant_figures = int(-np.floor(np.log10(ci_range)))
                significant_figures = max(1,significant_figures)
                formatted_median = float(f"{median_value:.{significant_figures}f}")
                formatted_range = float(f"{ci_range:.{significant_figures}f}")

                # Output the result
                print(f"{formatted_median} {formatted_range}", flush=True)

                # Append the result to the circular buffer and save to file
                if args.output != "":
                    sample_buffer.append(formatted_median)
                    np.savetxt(args.output, sample_buffer)
                    
                if args.plot != "":
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
                    plt.savefig(args.plot)
                    plt.close()
                
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        scale.cleanup()
        
if __name__ == "__main__":
    main()
