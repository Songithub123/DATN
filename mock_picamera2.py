"""
Mock picamera2 library for development on laptops
Same API as real picamera2, but prints actions instead of taking photos
"""

import time
from datetime import datetime

class Picamera2:
    """Mock camera that simulates real camera behavior"""
    
    def __init__(self):
        self._running = False
        self._recording = False
        self._config = None
        print("📷 [MOCK] Picamera2 initialized")
    
    def configure(self, config):
        """Mock configuration"""
        self._config = config
        print(f"📷 [MOCK] Camera configured: {config}")
    
    def create_still_configuration(self):
        """Return mock still configuration"""
        return {"mode": "still", "quality": "high"}
    
    def create_video_configuration(self):
        """Return mock video configuration"""
        return {"mode": "video", "fps": 30}
    
    def start(self):
        """Start camera"""
        self._running = True
        print("📷 [MOCK] Camera started")
        time.sleep(0.1)  # Simulate startup delay
    
    def stop(self):
        """Stop camera"""
        self._running = False
        print("📷 [MOCK] Camera stopped")
    
    def capture_file(self, filename):
        """Mock photo capture"""
        if not self._running:
            print("⚠️ [MOCK] Camera not started!")
            return
        
        print(f"📸 [MOCK] Photo captured: {filename}")
        
        # Optional: Create dummy file for testing
        with open(filename, 'w') as f:
            f.write(f"Mock photo from {datetime.now()}\n")
            f.write("This is a simulated image file")
        
        return True
    
    def start_recording(self, filename):
        """Mock video recording start"""
        if not self._running:
            print("⚠️ [MOCK] Camera not started!")
            return
        
        self._recording = True
        print(f"🎥 [MOCK] Recording started: {filename}")
    
    def stop_recording(self):
        """Mock video recording stop"""
        if self._recording:
            self._recording = False
            print("🎥 [MOCK] Recording stopped")
    
    def capture_array(self):
        """Mock capture as numpy array (for preview)"""
        print("📷 [MOCK] Captured array")
        import numpy as np
        return np.zeros((480, 640, 3), dtype=np.uint8)


# Mock exceptions
class PiCamera2Error(Exception):
    pass