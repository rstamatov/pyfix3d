import time
import traceback

def retry_operation(operation, attempts = 6, delay = 10):
    """
    Tries to execute the specified operation multiple times.
    If the operation fails, it retries after a specified delay.

    Arguments:
    - operation: A callable representing the operation to execute.
    - attempts: The maximum number of attempts.
    - delay: The delay (in seconds) between attempts.
    """
    for attempt in range(attempts):
        try:
            return operation()  # Attempt the operation
        except Exception as e:
            print(f"Attempt {attempt + 1} failed with error: {e}")
            if attempt < attempts - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise  # Reraises the last exception if out of attempts

from visualizer import *
from visualizer_gui import *

def initialize_visualizer(user_values):

    visualizer = Visualizer_3D(user_values[0] + "/*.tif",
                                    user_values[1] + "/*.tif",
                                    user_values[2] + "/*.tif",
                                    int(user_values[3]),
                                    int(user_values[4]),
                                    int(user_values[5]),
                                    spacing_x = float(user_values[6]),
                                    spacing_y = float(user_values[7]),
                                    spacing_z = float(user_values[8]))

    visualizer.start()
    return visualizer

user_values = PathChoice().prompt()

initialize_visualizer(user_values)

"""

try:
    # Use retry_operation to initialize the visualizer with retries
    retry_operation(lambda: initialize_visualizer(user_values), attempts = 6, delay=5)
except Exception:
    traceback.print_exc()
"""
