import serial
import struct
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import json
import re
import time

# Initialize global variables
time_data = []
x_data = []
y_data = []
z_data = []
packet_nums = []

# Serial setup
SERIAL_PORT = 'COM3'
BAUD_RATE = 115200

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)        

# Global variables for Binary calibration
firstBinLoop = True
calibration_start_time = None
calibration_data = {'x': [], 'y': [], 'z': []}
x_bin_diff, y_bin_diff, z_bin_diff = 0, 0, 0

# Global variables for ASCII calibration
firstAsciiLoop = True
ascii_calibration_start_time = None
ascii_calibration_data = {'x': [], 'y': [], 'z': []}
x_ascii_diff, y_ascii_diff, z_ascii_diff = 0, 0, 0

def read_binary(data):
    global firstBinLoop, calibration_start_time, x_bin_diff, y_bin_diff, z_bin_diff, calibration_data

    try:
        # Parse binary data
        header, packet_num, x, y, z = struct.unpack('<hhhhh', data)

        # Calibration phase
        if firstBinLoop:
            # Start the calibration timer if not already started
            if calibration_start_time is None:
                calibration_start_time = time.time()
                print("Starting binary calibration...")

            # Collect calibration data for 1 second
            calibration_data['x'].append(x)
            calibration_data['y'].append(y)
            calibration_data['z'].append(z)

            # Check if 1 second has passed
            if time.time() - calibration_start_time >= 1:
                # Calculate average offsets
                x_bin_diff = sum(calibration_data['x']) / len(calibration_data['x'])
                y_bin_diff = sum(calibration_data['y']) / len(calibration_data['y'])
                z_bin_diff = sum(calibration_data['z']) / len(calibration_data['z'])

                print(f"Calibration complete. Offsets - X: {x_bin_diff}, Y: {y_bin_diff}, Z: {z_bin_diff}")
                
                firstBinLoop = False
                calibration_start_time = None
                calibration_data = {'x': [], 'y': [], 'z': []}
                return False

            return False

        x_adj = x - x_bin_diff
        y_adj = y - y_bin_diff
        z_adj = z - z_bin_diff

        # Append to data lists
        time_data.append(len(time_data))
        x_data.append(x_adj)
        y_data.append(y_adj)
        z_data.append(z_adj)
        packet_nums.append(packet_num)

        # Keep only the last 1000 points for smooth plotting
        if len(time_data) > 1000:
            time_data.pop(0)
            x_data.pop(0)
            y_data.pop(0)
            z_data.pop(0)
            packet_nums.pop(0)

        print(f"Binary - Header: {header}, Packet num: {packet_num}")
        print(f"Binary - X: {x_adj:.3f}, Y: {y_adj:.3f}, Z: {z_adj:.3f}")

        return True
    except struct.error as e:
        print(f"Error parsing binary data: {e}")
        return False

def read_ascii(data):
    global firstAsciiLoop, ascii_calibration_start_time, x_ascii_diff, y_ascii_diff, z_ascii_diff, ascii_calibration_data

    try:
        # Decode the data as ASCII
        decoded_data = data.decode('ascii')
        
        # Use regex to extract clean JSON string
        json_match = re.search(r'\{[^}]+\}', decoded_data)
        if json_match:
            clean_json = json_match.group(0)

            # Parse the cleaned JSON
            parsed_data = json.loads(clean_json)
        
            # Extract X, Y, Z
            x = parsed_data.get("X", "N/A")
            y = parsed_data.get("Y", "N/A")
            z = parsed_data.get("Z", "N/A")

            # Calibration phase
            if firstAsciiLoop:
                # Start the calibration timer if not already started
                if ascii_calibration_start_time is None:
                    ascii_calibration_start_time = time.time()
                    print("Starting ASCII calibration...")
                    # Reset the calibration data list
                    ascii_calibration_data = {'x': [], 'y': [], 'z': []}

                # Collect calibration data for 1 second
                ascii_calibration_data['x'].append(float(x))
                ascii_calibration_data['y'].append(float(y))
                ascii_calibration_data['z'].append(float(z))

                # Check if 1 second has passed
                if time.time() - ascii_calibration_start_time >= 1:
                    # Calculate average offsets
                    x_ascii_diff = sum(ascii_calibration_data['x']) / len(ascii_calibration_data['x'])
                    y_ascii_diff = sum(ascii_calibration_data['y']) / len(ascii_calibration_data['y'])
                    z_ascii_diff = sum(ascii_calibration_data['z']) / len(ascii_calibration_data['z'])

                    print(f"ASCII Calibration complete. Offsets - X: {x_ascii_diff}, Y: {y_ascii_diff}, Z: {z_ascii_diff}")
                    
                    firstAsciiLoop = False
                    ascii_calibration_start_time = None
                    return False

                return False

            x_adj = float(x) - x_ascii_diff
            y_adj = float(y) - y_ascii_diff
            z_adj = float(z) - z_ascii_diff

            time_data.append(len(time_data))
            x_data.append(x_adj)
            y_data.append(y_adj)
            z_data.append(z_adj)

            # Keep only the last 1000 points for smooth plotting
            if len(time_data) > 1000:
                time_data.pop(0)
                x_data.pop(0)
                y_data.pop(0)
                z_data.pop(0)

            print(f"ASCII - X: {x_adj:.3f}, Y: {y_adj:.3f}, Z: {z_adj:.3f}")
            return True
        
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as e:
        print(f"Error decoding ASCII data: {e}")
        return False

def read_data():
    if ser.in_waiting > 0:
        # Get first byte
        data = ser.read(ser.in_waiting)
        
        # Check if the first byte is 0xAB - for binary data
        if data[0] != 0xAB:
            read_ascii(data)

def update_plot(frame):
    read_data() 

    ax.clear()
    ax.plot(time_data, x_data, label='X-axis')
    ax.set_title('Live Gyroscope Data')
    ax.set_xlabel('Time')
    ax.set_ylabel('Stride')
    ax.legend()

def main():
    global fig, ax
    fig, ax = plt.subplots()

    ani = FuncAnimation(fig, update_plot, interval=100)  # Update every 100 ms
    plt.show()

    ser.close()

if __name__ == "__main__":
    main()
