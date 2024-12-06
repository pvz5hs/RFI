import os
import sys
import argparse
import subprocess
import datetime
import time
import datetime


def create_data_folder():
    """Creates the data folder for today's date."""
    today = datetime.datetime.now().strftime("%d_%m_%Y")
    folder_path = os.path.expanduser(f"~/Desktop/Data/{today}")
    os.makedirs(folder_path, exist_ok=True)
    return folder_path


def compute_center_frequency(start_freq, bandwidth):
    """Computes the center frequency."""
    return start_freq + (bandwidth / 2)


def generate_filename(folder_path, min_freq, timestamp):
    """Generates a filename based on frequency and timestamp."""
    filename = f"{min_freq}_{timestamp}.txt"
    return os.path.join(folder_path, filename)

def get_total_runtime(startTime):
    currentTime = datetime.datetime.now()
    timeDifference = currentTime - startTime
    totalRuntime = timeDifference.total_seconds()
    return totalRuntime

def run_flowgraph(center_freq, sampling_rate, bandwidth, output_file, observation_interval, log_path, , start_time, observation_interval):
    """Runs the flowgraph script and stops it after the observation interval."""
    try:
        cmd = [
            "python3", os.path.expanduser("~/Desktop/RFI/flowgraph.py"),
            "--center_freq", str(center_freq),
            "--sampling_rate", str(sampling_rate),
            "--bandwidth", str(bandwidth),
            "--output_file", output_file
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        log_message(log_path, f"Started flowgraph (PID: {process.pid}) for center frequency {center_freq} Hz.")
        
        # Wait for the observation interval
        sleep_total = 0
        while sleep_total < observation_interval:
            time.sleep(1)
            if get_total_runtime(start_time) < observation_time:
                break
            sleep_total += 1
        
        
        # Attempt to terminate the process
        process.terminate()
        process.wait(timeout=5)
        log_message(log_path, f"Flowgraph terminated successfully (PID: {process.pid}).")
        time.sleep(10) # Let's wait 10 seocnds here
        return process.communicate()
    except subprocess.TimeoutExpired:
        # Force kill if the process doesn't terminate
        process.kill()
        log_message(log_path, f"Flowgraph (PID: {process.pid}) was forcefully terminated.")
        return None, f"Forcefully terminated process with PID {process.pid}"
    except Exception as e:
        return None, str(e)


def log_message(log_path, message):
    """Writes a log message to the log file and prints it."""
    with open(log_path, "a") as log_file:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"[{timestamp}] {message}\n")
    print(message)


def main():
    start_time = datetime.datetime.now()

    parser = argparse.ArgumentParser(description="Scheduler for flowgraph execution.")
    parser.add_argument("--start_freq", type=float, required=True, help="Starting frequency in Hz")
    parser.add_argument("--end_freq", type=float, required=True, help="Ending frequency in Hz")
    parser.add_argument("--bandwidth", type=float, required=True, help="Bandwidth in Hz")
    parser.add_argument("--sampling_rate", type=float, required=True, help="Sampling rate in Hz")
    parser.add_argument("--observation_interval", type=float, required=True, help="Observation interval in seconds")
    parser.add_argument("--observation_time", type=float, required=True, help="Total observation time in seconds")
    args = parser.parse_args()

    # Variables
    folder_path = create_data_folder()
    log_path = os.path.join(folder_path, "log.txt")
    log_message(log_path, "Scheduler started.")

    start_freq = args.start_freq
    end_freq = args.end_freq
    bandwidth = args.bandwidth
    sampling_rate = args.sampling_rate
    observation_interval = args.observation_interval
    observation_time = args.observation_time

    initial_start_freq = start_freq  # Preserve the initial start frequency
    total_runtime = 0

    while get_total_runtime(start_time) < observation_time:
        current_freq = start_freq

        while current_freq <= end_freq:
            center_freq = compute_center_frequency(current_freq, bandwidth)
            timestamp = datetime.datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
            output_file = generate_filename(folder_path, current_freq, timestamp)

            log_message(log_path, f"Running flowgraph for center frequency {center_freq} Hz...")
            output, error = run_flowgraph(center_freq, sampling_rate, bandwidth, output_file, observation_interval, log_path, start_time, observation_time)

            if error:
                log_message(log_path, f"Error: {error}. Retrying...")
                continue

            log_message(log_path, f"Flowgraph completed. Output: {output.strip() if output else 'No output.'}")
            current_freq += bandwidth
            if (get_total_runtime(start_time) >= observation_time):
                break
        # Reset frequencies for next loop
        start_freq = initial_start_freq
    
    log_message(log_path, "Observation complete. Scheduler terminated.")


if __name__ == "__main__":
    main()
