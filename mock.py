"""
test_main.py - Mock version for testing on laptop
All hardware calls are mocked, prints instead of actual hardware control
"""

import time
from datetime import datetime

# ===== MOCK HARDWARE LIBRARIES =====
class MockGPIO:
    """Mock RPi.GPIO for laptop testing"""
    BCM = 1
    OUT = 1
    IN = 1
    HIGH = 1
    LOW = 0
    PUD_UP = 1
    
    def __init__(self):
        self.pin_states = {}
        self.warnings = False
    
    def setmode(self, mode):
        print(f"[GPIO] Set mode to {mode}")
    
    def setwarnings(self, flag):
        self.warnings = flag
    
    def setup(self, pin, mode, pull_up_down=None):
        self.pin_states[pin] = self.LOW
        print(f"[GPIO] Pin {pin} setup as {'OUTPUT' if mode==self.OUT else 'INPUT'}")
    
    def output(self, pin, state):
        self.pin_states[pin] = state
        print(f"[GPIO] Pin {pin} → {'HIGH' if state else 'LOW'}")
    
    def input(self, pin):
        # Simulate button press every 5 seconds for testing
        if pin == 17:  # Button pin
            # Simulate button press every 5 seconds
            simulated_state = self.LOW if (int(time.time()) % 10) > 8 else self.HIGH
            return simulated_state
        return self.pin_states.get(pin, self.LOW)

class MockBusIO:
    """Mock I2C bus"""
    def __init__(self, scl, sda):
        print(f"[I2C] Bus created with SCL={scl}, SDA={sda}")

class MockADS1115:
    """Mock ADC for TDS and water level"""
    class P0: pass
    class P1: pass
    
    def __init__(self, i2c):
        print("[ADC] ADS1115 initialized (mock)")
        self.channels = {0: 1.5, 1: 2.0}  # Mock readings

class MockAnalogIn:
    """Mock analog channel"""
    def __init__(self, ads, pin):
        self.pin = pin
        print(f"[ADC] Channel {pin} created")
    
    @property
    def voltage(self):
        # Simulate slowly changing values
        t = time.time()
        if self.pin == 0:  # TDS channel
            # Simulate TDS rising then falling
            mock_voltage = 1.5 + (t % 20 - 10) / 10
            return max(0.5, min(3.0, mock_voltage))
        else:  # Water level channel
            # Simulate water level dropping slowly
            mock_voltage = 2.5 - (t % 60) / 60
            return max(0.5, min(3.0, mock_voltage))

class MockW1ThermSensor:
    """Mock temperature sensor"""
    def get_temperature(self):
        # Simulate room temperature with small variations
        t = time.time()
        return 25.0 + (t % 30 - 15) / 30

class MockOLED:
    """Mock OLED display"""
    def __init__(self, i2c):
        print("[OLED] Display initialized (mock)")
    
    def fill(self, color):
        pass
    
    def text(self, text, x, y, color):
        # Print to console instead of real display
        print(f"[OLED] [{y:2d}] {text}")
    
    def show(self):
        pass

class MockCamera:
    """Mock camera"""
    def __init__(self):
        print("[Camera] Camera initialized (mock)")
    
    def configure(self, config):
        pass
    
    def create_still_configuration(self):
        return {}
    
    def start(self):
        print("[Camera] Camera started (mock)")
    
    def capture_file(self, filename):
        print(f"[Camera] 📸 Would save: {filename}")
        # Actually create dummy file for testing
        with open(filename, 'w') as f:
            f.write(f"Mock photo from test at {datetime.now()}\n")

# ===== TASK TIMER (REAL - works on laptop) =====
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

# ===== PID (REAL - works on laptop) =====
from simple_pid import PID

# ===== MOCK HARDWARE INSTANCES =====
GPIO = MockGPIO()
busio = type('busio', (), {'I2C': MockBusIO})()
board = type('board', (), {'SCL': 3, 'SDA': 2})()
adafruit_ads1x15 = type('mod', (), {'ads1115': MockADS1115})()
AnalogIn = MockAnalogIn
W1ThermSensor = MockW1ThermSensor
ssd1306 = lambda i2c: MockOLED(i2c)
Picamera2 = type('mod', (), {'Picamera2': MockCamera})()

# ===== YOUR ACTUAL CODE (copy from main.py) =====
# But with try/except removed since we have mocks

# Pin definitions
BUTTON_PIN = 17
DS18B20_PIN = 4
RELAY_HEATER = 22
RELAY_PUMP = 23
RELAY_VALVE = 24

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(DS18B20_PIN, GPIO.IN)
GPIO.setup(RELAY_HEATER, GPIO.OUT)
GPIO.setup(RELAY_PUMP, GPIO.OUT)
GPIO.setup(RELAY_VALVE, GPIO.OUT)

# Initialize relays OFF
GPIO.output(RELAY_HEATER, GPIO.LOW)
GPIO.output(RELAY_PUMP, GPIO.LOW)
GPIO.output(RELAY_VALVE, GPIO.LOW)

# Setup I2C and sensors
i2c = busio.I2C(board.SCL, board.SDA)
temperature_sensor = W1ThermSensor()
ads = MockADS1115(i2c)

# Analog channels
tds_channel = AnalogIn(ads, 0)  # ADS.P0
water_channel = AnalogIn(ads, 1)  # ADS.P1

# Setup OLED
oled = ssd1306(i2c)

# Setup camera
camera = MockCamera()
camera.configure(camera.create_still_configuration())
camera.start()

# Calibration constants
TDS_VOLTAGE_TO_PPM = 500
WATER_VOLTAGE_TO_PERCENT = 100 / 3.3

# Setup PID controllers
pid_temp = PID(Kp=5.0, Ki=0.5, Kd=1.0, setpoint=25.0)
pid_temp.output_limits = (0, 100)

pid_tds = PID(Kp=2.0, Ki=0.1, Kd=0.5, setpoint=400)
pid_tds.output_limits = (0, 100)

# State variables
counting_mode = False
tds_ppm = 0
water_percent = 0
temperature = 0

# Button debounce variables
last_button_state = GPIO.HIGH

# Create timers
button_check_timer = TaskTimer(0.05)   # Check button every 50ms
sensor_timer = TaskTimer(2.0)          # Read sensors every 2 seconds
display_timer = TaskTimer(1.0)         # Update display every 1 second
control_timer = TaskTimer(0.5)         # PID control every 0.5 seconds
camera_timer = TaskTimer(10.0)         # Take photo every 10 seconds (for testing)

print("\n" + "="*50)
print("TEST MODE - Running on Laptop (No hardware required)")
print("="*50 + "\n")

# Counter to stop after N loops (for testing)
test_loops = 0
MAX_TEST_LOOPS = 30  # Run for ~15 seconds then stop

try:
    while test_loops < MAX_TEST_LOOPS:
        print(f"\n--- Loop {test_loops+1} ---")
        
        # === BUTTON WITH DEBOUNCE ===
        if button_check_timer.check():
            current_button_state = GPIO.input(BUTTON_PIN)
            print(f"  Button state: {'PRESSED' if current_button_state == GPIO.LOW else 'released'}")
            
            # Detect falling edge (HIGH → LOW = button press)
            if last_button_state == GPIO.HIGH and current_button_state == GPIO.LOW:
                counting_mode = not counting_mode
                print(f"  🔘 BUTTON PRESSED! Counting Mode: {'ON' if counting_mode else 'OFF'}")
            
            last_button_state = current_button_state
        
        # === SENSOR READING ===
        if sensor_timer.check():
            tds_voltage = tds_channel.voltage
            tds_ppm = tds_voltage * TDS_VOLTAGE_TO_PPM
            
            water_voltage = water_channel.voltage
            water_percent = water_voltage * WATER_VOLTAGE_TO_PERCENT
            water_percent = max(0, min(100, water_percent))
            
            temperature = temperature_sensor.get_temperature()
            
            print(f"  📊 Sensors: TDS={tds_ppm:.0f}ppm, Water={water_percent:.0f}%, Temp={temperature:.1f}°C")
        
        # === PID CONTROL ===
        if control_timer.check():
            if counting_mode:
                GPIO.output(RELAY_PUMP, GPIO.HIGH)
                GPIO.output(RELAY_VALVE, GPIO.HIGH)
                print(f"  🔧 MANUAL MODE: Pump ON, Valve ON")
            else:
                # Temperature control
                heater_power = pid_temp(temperature)
                if heater_power > 30:
                    GPIO.output(RELAY_HEATER, GPIO.HIGH)
                    print(f"  🌡️ Heater: ON ({heater_power:.0f}%)")
                else:
                    GPIO.output(RELAY_HEATER, GPIO.LOW)
                
                # TDS control
                pump_power = pid_tds(tds_ppm)
                if tds_ppm > 420:  # Setpoint + 20
                    GPIO.output(RELAY_PUMP, GPIO.HIGH)
                    print(f"  💧 Pump: ON (TDS {tds_ppm:.0f} > 420)")
                elif tds_ppm < 380:  # Setpoint - 20
                    GPIO.output(RELAY_PUMP, GPIO.LOW)
                    print(f"  💧 Pump: OFF (TDS {tds_ppm:.0f} < 380)")
                
                # Water level control
                if water_percent < 20:
                    GPIO.output(RELAY_VALVE, GPIO.HIGH)
                    print(f"  🚰 Valve: OPEN (Water {water_percent:.0f}%)")
                elif water_percent > 80:
                    GPIO.output(RELAY_VALVE, GPIO.LOW)
                    print(f"  🚰 Valve: CLOSED (Water {water_percent:.0f}%)")
        
        # === DISPLAY UPDATE ===
        if display_timer.check():
            print("\n  📟 OLED DISPLAY:")
            print(f"  ┌{'─'*26}┐")
            print(f"  │ Temp: {temperature:.1f}°C{' '*(18-len(str(temperature)))}│")
            print(f"  │ TDS: {tds_ppm:.0f}ppm{' '*(18-len(str(tds_ppm)))}│")
            print(f"  │ Water: {water_percent:.0f}%{' '*(17-len(str(water_percent)))}│")
            print(f"  │ Mode: {'MANUAL' if counting_mode else 'AUTO'}{' '*(18-(6 if counting_mode else 4))}│")
            print(f"  └{'─'*26}┘")
        
        # === CAMERA ===
        if camera_timer.check():
            filename = f"test_photo_{datetime.now().strftime('%H%M%S')}.txt"
            camera.capture_file(filename)
        
        time.sleep(0.1)
        test_loops += 1
    
    print("\n" + "="*50)
    print("✅ TEST COMPLETE! All systems passed mock testing.")
    print(f"📊 Simulated {test_loops} loops ({(test_loops*0.1):.1f} seconds)")
    print("="*50)

except KeyboardInterrupt:
    print("\n\n⚠️ Test interrupted by user")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()