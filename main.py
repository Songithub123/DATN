import RPi.GPIO as GPIO
import time
from board import SDA, SCL
import board
import busio
from luma.oled.device import ssd1306
from luma.core.render import canvas
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from w1thermsensor import W1ThermSensor
from simple_pid import PID
import bluetooth
import my_bluetooth

# Mock camera for development
try:
    from picamera2 import Picamera2
    USE_REAL_CAMERA = True
except ImportError:
    import mock_picamera2 as Picamera2
    USE_REAL_CAMERA = False

# Pin definitions
BUTTON_PIN = 17
DS18B20_PIN = 4
RELAY_HEATER = 22
RELAY_PUMP = 23
RELAY_VALVE = 24

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # PUD_UP = LOW when pressed
GPIO.setup(DS18B20_PIN, GPIO.IN)
GPIO.setup(RELAY_HEATER, GPIO.OUT)
GPIO.setup(RELAY_PUMP, GPIO.OUT)
GPIO.setup(RELAY_VALVE, GPIO.OUT)

# Initialize all relays OFF
GPIO.output(RELAY_HEATER, GPIO.LOW)
GPIO.output(RELAY_PUMP, GPIO.LOW)
GPIO.output(RELAY_VALVE, GPIO.LOW)

# Setup I2C and sensors
i2c = busio.I2C(SCL, SDA)
temperature_sensor = W1ThermSensor()
ads = ADS.ADS1115(i2c)

# Analog channels
tds_channel = AnalogIn(ads, ADS.P0)
water_channel = AnalogIn(ads, ADS.P1)

# Setup OLED
oled = ssd1306(i2c)

# Setup PID controllers
pid_temp = PID(Kp=5.0, Ki=0.5, Kd=1.0, setpoint=25.0)
pid_temp.output_limits = (0, 100)

pid_tds = PID(Kp=2.0, Ki=0.1, Kd=0.5, setpoint=400)
pid_tds.output_limits = (0, 100)

pid_water = PID(Kp=1.0, Ki=0.05, Kd=0.2, setpoint=2.5)
pid_water.output_limits = (0, 100)

# Setup camera
camera = Picamera2.Picamera2()
camera.configure(camera.create_still_configuration())
camera.start()

# Calibration constants
TDS_VOLTAGE_TO_PPM = 500
WATER_VOLTAGE_TO_PERCENT = 100 / 3.3

# State variables
counting_mode = False
tds_ppm = 0
water_percent = 0
temperature = 0
fish_count = 0

# Button debounce variables
last_button_state = GPIO.HIGH  # Start with NOT pressed (PUD_UP = HIGH when not pressed)
button_pressed = False

# Task Timer class
class TaskTimer:
    def __init__(self, interval):
        self.interval = interval
        self.last_time = time.monotonic()
    
    def check(self):
        current_time = time.monotonic()
        if current_time - self.last_time >= self.interval:
            self.last_time = current_time
            return True
        return False

# Create timers
button_check_timer = TaskTimer(0.05)   # Check button every 50ms (fast)
sensor_timer = TaskTimer(2.0)          # Read sensors every 2 seconds
display_timer = TaskTimer(1.0)         # Update display every 1 second
control_timer = TaskTimer(0.5)         # PID control every 0.5 seconds
camera_timer = TaskTimer(60.0)         # Take photo every minute

#Bluetooth setup
bt_client_sock = None
my_bluetooth.setup_bluetooth()

print("System Started!")
print(f"Camera: {'REAL' if USE_REAL_CAMERA else 'MOCK'}")
print(f"Target Temp: {pid_temp.setpoint}°C")
print(f"Target TDS: {pid_tds.setpoint}ppm")

# Main loop
while True:
    # === BUTTON WITH DEBOUNCE ===
    if button_check_timer.check():
        current_button_state = GPIO.input(BUTTON_PIN)
        
        # Detect falling edge (HIGH → LOW = button press)
        if last_button_state == GPIO.HIGH and current_button_state == GPIO.LOW:
            # Button pressed! Toggle mode
            counting_mode = not counting_mode
            print(f"🔘 Button pressed! Counting Mode: {'ON' if counting_mode else 'OFF'}")
            # Wait a bit to debounce (already handled by timer, but add small delay)
            time.sleep(0.05)
        
        last_button_state = current_button_state
    
    # === SENSOR READING ===
    if sensor_timer.check():
        # Read TDS
        tds_voltage = tds_channel.voltage
        tds_ppm = tds_voltage * TDS_VOLTAGE_TO_PPM
        
        # Read Water Level
        water_voltage = water_channel.voltage
        water_percent = water_voltage * WATER_VOLTAGE_TO_PERCENT
        water_percent = max(0, min(100, water_percent))
        
        # Read Temperature
        temperature = temperature_sensor.get_temperature()
        
        print(f"📊 Sensors: {temperature:.1f}°C, {tds_ppm:.0f}ppm, {water_percent:.0f}%")
        my_bluetooth.send_bluetooth_data(temperature, tds_ppm, water_percent,
                            fish_count=fish_count,
                            counting_mode=counting_mode,
                            relay_heater=GPIO.input(RELAY_HEATER),
                            relay_pump=GPIO.input(RELAY_PUMP),
                            relay_valve=GPIO.input(RELAY_VALVE))
        
    # === PID CONTROL ===
    if control_timer.check():
        if counting_mode:
            # Manual control mode
            GPIO.output(RELAY_PUMP, GPIO.HIGH)
            GPIO.output(RELAY_VALVE, GPIO.HIGH)
            print("🔧 Manual mode: Pump ON, Valve ON")
        else:
            # Automatic PID control mode
            
            # Temperature control
            heater_power = pid_temp(temperature)
            if heater_power > 30:
                GPIO.output(RELAY_HEATER, GPIO.HIGH)
                print(f"🔥 Heater: ON ({heater_power:.0f}%)")
            else:
                GPIO.output(RELAY_HEATER, GPIO.LOW)
            
            # TDS control (with hysteresis)
            if tds_ppm > pid_tds.setpoint + 20:
                GPIO.output(RELAY_PUMP, GPIO.HIGH)
                print(f"💧 Pump: ON (TDS {tds_ppm:.0f} > {pid_tds.setpoint})")
            elif tds_ppm < pid_tds.setpoint - 20:
                GPIO.output(RELAY_PUMP, GPIO.LOW)
                print(f"💧 Pump: OFF (TDS {tds_ppm:.0f} < {pid_tds.setpoint})")
            
            # Water level control
            if water_percent < 20:
                GPIO.output(RELAY_VALVE, GPIO.HIGH)
                print(f"🚰 Valve: OPEN (Water {water_percent:.0f}%)")
            elif water_percent > 80:
                GPIO.output(RELAY_VALVE, GPIO.LOW)
                print(f"🚰 Valve: CLOSED (Water {water_percent:.0f}%)")
    
    # === DISPLAY UPDATE ===
    if display_timer.check():
        with canvas(oled) as draw:
            draw.rectangle((0, 0, 128, 64), outline=1, fill=0)
            draw.text((2, 2), f"Temp:{temperature:.1f}C", fill=1)
            draw.text((2, 14), f"TDS:{tds_ppm:.0f}ppm", fill=1)
            draw.text((2, 26), f"Water:{water_percent:.0f}%", fill=1)
            draw.text((2, 38), f"Mode:{'MANUAL' if counting_mode else 'AUTO'}", fill=1)
            
            # Show relay status
            status = ""
            if GPIO.input(RELAY_HEATER):
                status += "H"
            if GPIO.input(RELAY_PUMP):
                status += "P"
            if GPIO.input(RELAY_VALVE):
                status += "V"
            draw.text((2, 52), f"Relays:{status}", fill=1)
    
    # === CAMERA ===
    if camera_timer.check():
        filename = f"log_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
        camera.capture_file(filename)
        print(f"📸 Photo saved: {filename}")
    
    # Small delay
    time.sleep(0.01)