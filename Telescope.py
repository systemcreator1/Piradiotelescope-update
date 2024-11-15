import tkinter as tk
import numpy as np
import matplotlib.pyplot as plt
from rtlsdr import RtlSdr
from scipy.signal import butter, lfilter
import RPi.GPIO as GPIO
import time
import csv

# GPIO setup for motors
AZIMUTH_PIN = 18  # Horizontal (azimuth)
ELEVATION_PIN = 23  # Vertical (elevation)
GPIO.setmode(GPIO.BCM)
GPIO.setup(AZIMUTH_PIN, GPIO.OUT)
GPIO.setup(ELEVATION_PIN, GPIO.OUT)
azimuth_pwm = GPIO.PWM(AZIMUTH_PIN, 50)
elevation_pwm = GPIO.PWM(ELEVATION_PIN, 50)
azimuth_pwm.start(0)
elevation_pwm.start(0)

# SDR Setup
sdr = RtlSdr()
sdr.sample_rate = 2.048e6
sdr.center_freq = 1420e6  # Example frequency
sdr.gain = 49.6

# Amplify signal function
def amplify_signal(signal, factor=10):
    return signal * factor

# Lowpass filter
def butter_lowpass_filter(data, cutoff, fs, order=5):
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return lfilter(b, a, data)

# Servo control functions
def set_servo_angle(pwm, angle):
    duty_cycle = 2 + (angle / 18)
    pwm.ChangeDutyCycle(duty_cycle)
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0)

# Function to start scanning
def start_scanning():
    azimuth = azimuth_slider.get()
    elevation = elevation_slider.get()
    set_servo_angle(azimuth_pwm, azimuth)
    set_servo_angle(elevation_pwm, elevation)

    # Record position and frequency data
    with open("scan_data.csv", "a") as file:
        writer = csv.writer(file)

        # Frequency sweep range
        frequency_range = np.linspace(1400e6, 1430e6, 100)

        for freq in frequency_range:
            sdr.center_freq = freq
            samples = sdr.read_samples(256*1024)

            # Amplify and filter signal
            amplified_samples = amplify_signal(samples, factor=15)
            filtered_samples = butter_lowpass_filter(amplified_samples, cutoff=0.1 * sdr.sample_rate, fs=sdr.sample_rate)

            # Calculate FFT and power
            fft_result = np.fft.fftshift(np.fft.fft(filtered_samples))
            power = np.abs(fft_result)**2

            # Save azimuth, elevation, frequency, and power
            writer.writerow([azimuth, elevation, freq, np.max(power)])

            # Update frequency display
            update_frequency(freq)

            # Live plotting
            plt.clf()
            plt.plot(np.fft.fftshift(np.fft.fftfreq(len(filtered_samples), 1/sdr.sample_rate)), power)
            plt.xlabel('Frequency (Hz)')
            plt.ylabel('Power')
            plt.title(f'Frequency Spectrum at {freq/1e6} MHz, Azimuth: {azimuth}, Elevation: {elevation}')
            plt.grid()
            plt.pause(0.1)
    plt.show()

# UI setup
root = tk.Tk()
root.title("Telescope control panel")

# Information Display Frame
info_frame = tk.Frame(root, relief=tk.SUNKEN, bd=1)
info_frame.pack(fill=tk.X, padx=10, pady=10)

# Frequency Display Label
freq_label = tk.Label(info_frame, text="Current Frequency: - MHz")
freq_label.pack(side=tk.LEFT)

# Azimuth and Elevation Display Labels
azimuth_label = tk.Label(info_frame, text="Azimuth: -")
azimuth_label.pack(side=tk.LEFT, padx=10)
elevation_label = tk.Label(info_frame, text="Elevation: -")
elevation_label.pack(side=tk.LEFT, padx=10)

# Control Frame
control_frame = tk.Frame(root)
control_frame.pack(fill=tk.X, padx=10, pady=10)

# Azimuth Control
tk.Label(control_frame, text="Azimuth Control (0-180)").grid(row=0, column=0)
azimuth_slider = tk.Scale(control_frame, from_=0, to=180, orient=tk.HORIZONTAL, command=lambda val: update_azimuth_label(val))
azimuth_slider.grid(row=1, column=0)

# Elevation Control
tk.Label(control_frame, text="Elevation Control (0-180)").grid(row=0, column=1)
elevation_slider = tk.Scale(control_frame, from_=0, to=180, orient=tk.HORIZONTAL, command=lambda val: update_elevation_label(val))
elevation_slider.grid(row=1, column=1)

# Scan Button
scan_button = tk.Button(control_frame, text="Start Scanning", command=start_scanning)
scan_button.grid(row=2, columnspan=2)

# Update label functions
def update_azimuth_label(value):
    azimuth_label.config(text=f"Azimuth: {value}")

def update_elevation_label(value):
    elevation_label.config(text=f"Elevation: {value}")

def update_frequency(freq):
    freq_label.config(text=f"Current Frequency: {freq/1e6} MHz")

# Cleanup and close UI
def on_closing():
    azimuth_pwm.stop()
    elevation_pwm.stop()
    GPIO.cleanup()
    sdr.close()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
