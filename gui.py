import paramiko
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QPushButton, QInputDialog, QMessageBox, QTextEdit
)
from PyQt5.QtCore import Qt
import threading
import os
import signal
from PyQt5.QtCore import QThread, pyqtSignal
import re

class WorkerThread(QThread):
    # Define signals for success and error handling
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, command, ssh_client):
        super().__init__()
        self.command = command
        self.ssh_client = ssh_client

    def run(self):
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(self.command)
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()

            if output:
                self.finished.emit(f"Command Output: {output}")
            if error:
                self.error.emit(f"Command Error: {error}")
            if not error and not output:
                self.finished.emit("Scheduler process started successfully on the remote server.")
        except Exception as e:
            self.error.emit(f"Error executing the command: {e}")



class SDRControlGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SDR Control Panel")
        self.setGeometry(100, 100, 800, 600)


        # SSH client
        self.ssh_client = None
        self.log_thread = None
        self.stop_log = threading.Event()
        self.ssh_client = None  # Initialize ssh_client to None at the start
        self.is_logged_in = False

        # Main layout
        self.main_layout = QVBoxLayout()
        
        # Frequency input section
        start_freq_layout = QHBoxLayout()
        self.start_freq_label = QLabel("Start Frequency:")
        self.start_freq_input = QLineEdit()
        self.start_freq_input.setPlaceholderText("Enter value")
        self.start_freq_unit = QComboBox()
        self.start_freq_unit.addItems(["Hz", "kHz", "MHz", "GHz"])
        
        start_freq_layout.addWidget(self.start_freq_label)
        start_freq_layout.addWidget(self.start_freq_input)
        start_freq_layout.addWidget(self.start_freq_unit)
        self.main_layout.addLayout(start_freq_layout)

        end_freq_layout = QHBoxLayout()
        self.end_freq_label = QLabel("End Frequency:")
        self.end_freq_input = QLineEdit()
        self.end_freq_input.setPlaceholderText("Enter value")
        self.end_freq_unit = QComboBox()
        self.end_freq_unit.addItems(["Hz", "kHz", "MHz", "GHz"])
        
        end_freq_layout.addWidget(self.end_freq_label)
        end_freq_layout.addWidget(self.end_freq_input)
        end_freq_layout.addWidget(self.end_freq_unit)
        self.main_layout.addLayout(end_freq_layout)
        
        # Bandwidth input section
        bw_layout = QHBoxLayout()
        self.bw_label = QLabel("Bandwidth (Step Size):")
        self.bw_input = QLineEdit()
        self.bw_input.setPlaceholderText("Enter value")
        self.bw_unit = QComboBox()
        self.bw_unit.addItems(["Hz", "kHz", "MHz", "GHz"])
        
        bw_layout.addWidget(self.bw_label)
        bw_layout.addWidget(self.bw_input)
        bw_layout.addWidget(self.bw_unit)
        self.main_layout.addLayout(bw_layout)
        
        # Sampling rate input section
        sr_layout = QHBoxLayout()
        self.sr_label = QLabel("Sampling Rate:")
        self.sr_input = QLineEdit()
        self.sr_input.setPlaceholderText("Enter value")
        self.sr_unit = QComboBox()
        self.sr_unit.addItems(["Hz", "kHz", "MHz", "GHz"])
        
        sr_layout.addWidget(self.sr_label)
        sr_layout.addWidget(self.sr_input)
        sr_layout.addWidget(self.sr_unit)
        self.main_layout.addLayout(sr_layout)

        # Observation interval input section
        oi_layout = QHBoxLayout()
        self.oi_label = QLabel("Observation Intervals:")
        self.oi_input = QLineEdit()
        self.oi_input.setPlaceholderText("Enter value")
        self.oi_unit = QComboBox()
        self.oi_unit.addItems(["Seconds", "Minutes"])

        oi_layout.addWidget(self.oi_label)
        oi_layout.addWidget(self.oi_input)
        oi_layout.addWidget(self.oi_unit)
        self.main_layout.addLayout(oi_layout)

        # Observation time input section
        ot_layout = QHBoxLayout()
        self.ot_label = QLabel("Observation Time:")
        self.ot_input = QLineEdit()
        self.ot_input.setPlaceholderText("Enter value")
        self.ot_unit = QComboBox()
        self.ot_unit.addItems(["Seconds", "Minutes", "Hours", "Days"])
        
        ot_layout.addWidget(self.ot_label)
        ot_layout.addWidget(self.ot_input)
        ot_layout.addWidget(self.ot_unit)
        self.main_layout.addLayout(ot_layout)
        
        # Login button
        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.login_to_server)
        self.main_layout.addWidget(self.login_button, alignment=Qt.AlignCenter)

        # Stream button
        self.stream_button = QPushButton("Stream")
        self.stream_button.clicked.connect(self.apply_changes)
        self.main_layout.addWidget(self.stream_button, alignment=Qt.AlignCenter)

        # Log box
        log_boxes_layout = QHBoxLayout()

        # Add the command input layout to the main layout (above the Live Log box)
        command_input_layout = QHBoxLayout()

        # Command Input Box
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter a command to execute on the Linux box")
        self.command_input.returnPressed.connect(self.execute_user_command)  # Connect Enter key to execute_command
        command_input_layout.addWidget(self.command_input)
        self.main_layout.addLayout(command_input_layout)

        # Log box
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("background-color: #f4f4f4; color: black;")
        self.log_box.setPlaceholderText("General Log Viewer")  # Optional placeholder text
        log_boxes_layout.addWidget(self.log_box)

        # Add the log boxes layout to the main layout
        self.main_layout.addLayout(log_boxes_layout)
        # Set main layout
        self.setLayout(self.main_layout)
    
    def log_message(self, message):
        """Append a message to the log box."""
        self.log_box.append(message)
        print(message)
    
    def login_to_server(self):
        if self.is_logged_in:
            self.log_message("Already logged in.")
            return

        # Prompt user for server password
        password, ok = QInputDialog.getText(self, "Login", "Enter server password:", QLineEdit.Password)
        if ok and password:
            try:
                self.ssh_client = paramiko.SSHClient()
                self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.ssh_client.connect("172.27.155.167", username="sdr-user", password=password)
                self.is_logged_in = True  # Set the flag to True once logged in successfully
                self.log_message("Login successful!")
            except Exception as e:
                self.log_message(f"Error logging into server: {e}")
        else:
            self.log_message("Login canceled or no password entered.")
    
    def execute_command(self, command):
        if self.ssh_client:
            try:
                self.log_message(f"Executing command: {command}")
                stdin, stdout, stderr = self.ssh_client.exec_command(command)
                output = stdout.read().decode().strip()
                error = stderr.read().decode().strip()
                if output:
                    self.log_message(f"Command Output: {output}")
                if error:
                    self.log_message(f"Command Error: {error}")
                return output, error
            except Exception as e:
                self.log_message(f"Command execution failed: {e}")
                return None, str(e)
        else:
            self.log_message("Not logged in. Please log in first.")
            return None, "No SSH connection"

    def execute_user_command(self):
        command = self.command_input.text().strip()
        self.execute_command(command)
        self.command_input.clear()
        

    def convert_to_hz(self, value, unit):
        if unit == "Hz":
            return value
        elif unit == "kHz":
            return value * 1e3
        elif unit == "MHz":
            return value * 1e6
        elif unit == "GHz":
            return value * 1e9
        else:
            raise ValueError("Invalid unit selected.")

    def convert_to_seconds(self, value, unit):
        if unit == "Seconds":
            return value
        elif unit == "Minutes":
            return value * 60
        elif unit == "Hours":
            return value * 3600
        elif unit == "Days":
            return value * 86400
        else:
            raise ValueError("Invalid unit selected.")
    
    def closeEvent(self, event):
        self.stop_log.set()
        if self.log_thread:
            self.log_thread.join()
        if self.ssh_client:
            self.log_message("Closing SSH connection...")
            self.ssh_client.close()
        event.accept()


    def extract_info(self, log_line):
        # Regular expression pattern to extract the required information
        pattern = re.compile(r"PID: (\d+), Running Time: ([\d:]+), Command: python3 .+ --start_freq (\d+\.\d+) --end_freq (\d+\.\d+) --bandwidth (\d+\.\d+) --sampling_rate ([\d\.]+) --observation_time ([\d\.]+) --observation_interval ([\d\.]+)")
        
        # Match the log line against the pattern
        match = pattern.search(log_line)
        
        if match:
            pid = match.group(1)
            running_time = match.group(2)
            start_freq = match.group(3)
            end_freq = match.group(4)
            bandwidth = match.group(5)
            sample_rate = match.group(6)
            observation_time = match.group(7)
            observation_interval = match.group(8)

            # Format the output
            formatted_string = f"Process ID: {pid}\n" \
                            f"Running Time: {running_time}\n" \
                            f"Start Frequency: {start_freq} Hz\n" \
                            f"End Frequency: {end_freq} Hz\n" \
                            f"Bandwidth: {bandwidth} Hz\n" \
                            f"Sample Rate: {sample_rate} Hz\n" \
                            f"Observation Time: {observation_time} seconds\n" \
                            f"Observation Interval: {observation_interval} seconds"
            return formatted_string
        else:
            return "No match found in the log line."


    from PyQt5.QtWidgets import QMessageBox

    def ask_to_kill_process(self, process_info):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setText("A process is already running:")

        process_string = self.extract_info(process_info)
        msg.setInformativeText(process_string)
        msg.setWindowTitle("Process Running")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        yes_button = msg.button(QMessageBox.Yes)
        no_button = msg.button(QMessageBox.No)
        yes_button.setStyleSheet("""
            background-color: lightblue;
            color: black;
            font-weight: bold;
        """)
        no_button.setStyleSheet("""
            background-color: none;
            color: black;
            font-weight: normal;
        """)
        msg.setDefaultButton(QMessageBox.Yes)
        response = msg.exec_()

        if response == QMessageBox.Yes:
            return True
        else:
            return False

    def check_and_handle_running_instance(self):
        # Check for running instance
        command = 'ps aux | grep "python3 $HOME/Desktop/RFI/scheduler.py" | grep -v grep'
        output, error = self.execute_command(command)
        
        if error:
            self.log_message(f"Error checking for running instances: {error}")
            return False
        
        if output:
            # Extract PID and elapsed time
            lines = output.strip().split("\n")
            process_info = []
            for line in lines:
                parts = line.split()
                pid = parts[1]
                
                # Get elapsed time
                elapsed_time_command = f"ps -o etime= -p {pid}"
                elapsed_time_output, _ = self.execute_command(elapsed_time_command)
                elapsed_time = elapsed_time_output.strip()

                # (Optional) Parse command-line arguments from the running process
                process_details = " ".join(parts[10:])
                process_info.append(f"PID: {pid}, Running Time: {elapsed_time}, Command: {process_details}")
            
            # Show details and ask to kill
            details = "\n".join(process_info)
            if self.ask_to_kill_process(details):
                for line in process_info:
                    pid = line.split(",")[0].split(":")[1].strip()
                    kill_command = f"kill -9 {pid}"
                    _, kill_error = self.execute_command(kill_command)
                    if kill_error:
                        self.log_message(f"Error killing process {pid}: {kill_error}")
                    else:
                        self.log_message(f"Process {pid} killed.")
                return True
            else:
                return False
        else:
            self.log_message("No running instances found.")
            return True

    def apply_changes(self):
        if not self.ssh_client:
            self.log_message("Not logged in. Please log in first.")
            return



        # Retrieve and convert input values
        start_freq_value = self.start_freq_input.text()
        start_freq_unit = self.start_freq_unit.currentText()
        end_freq_value = self.end_freq_input.text()
        end_freq_unit = self.end_freq_unit.currentText()
        bandwidth_value = self.bw_input.text()
        bw_unit = self.bw_unit.currentText()
        sampling_rate_value = self.sr_input.text()
        sr_unit = self.sr_unit.currentText()
        observation_interval = self.oi_input.text()
        observation_interval_unit = self.oi_unit.currentText()
        observation_time = self.ot_input.text()
        observation_time_unit = self.ot_unit.currentText()

        try:
            # Convert input values to the appropriate units (Hz for frequencies, seconds for time)
            start_freq_in_hz = self.convert_to_hz(float(start_freq_value), start_freq_unit)
            end_freq_in_hz = self.convert_to_hz(float(end_freq_value), end_freq_unit)
            bw_in_hz = self.convert_to_hz(float(bandwidth_value), bw_unit)
            sr_in_hz = self.convert_to_hz(float(sampling_rate_value), sr_unit)
            observation_time_in_seconds = self.convert_to_seconds(float(observation_time), observation_time_unit)
            observation_interval_in_seconds = self.convert_to_seconds(float(observation_interval), observation_interval_unit)
            if observation_interval_in_seconds > observation_time_in_seconds:
                self.log_message(f"ERROR: Time Interval > Observation Time")
                return
            if start_freq_in_hz > end_freq_in_hz:
                self.log_message(f'ERROR: Start Frequency Higher Than End Frequency')
                return

            can_proceed = self.check_and_handle_running_instance()
            if not can_proceed:
                self.log_message("Stream canceled by user.")
                return
            
            # Build the command to execute on the remote Linux machine
            command = f"nohup python3 ~/Desktop/RFI/scheduler.py --start_freq {start_freq_in_hz} --end_freq {end_freq_in_hz} --bandwidth {bw_in_hz} --sampling_rate {sr_in_hz} --observation_time {observation_time_in_seconds} --observation_interval {observation_interval_in_seconds} &"
            
            # Create the worker thread to execute the command
            self.log_message(f"Starting background task to execute command: {command}")
            self.worker_thread = WorkerThread(command, self.ssh_client)
            self.worker_thread.finished.connect(self.log_message)
            self.worker_thread.error.connect(self.log_message)
            
            # Start the worker thread
            self.worker_thread.start()

        except ValueError:
            self.log_message("Invalid input. Please enter numeric values.")
        except Exception as e:
            self.log_message(f"Error preparing the command: {e}")



if __name__ == "__main__":
    app = QApplication([])
    gui = SDRControlGUI()
    gui.show()
    app.exec_()
