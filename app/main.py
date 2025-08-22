#!/usr/bin/env python3

import time
import logging
import threading
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymavlink import mavutil
import requests
import os

app = Flask(__name__, static_folder='static')
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArduSubController:
    def __init__(self):
        self.mavlink_connection = None
        self.vehicle_armed = False
        self.vehicle_mode = None
        self.heartbeat_received = False
        self.connection_thread = None
        self.running = False
        
    def connect_to_vehicle(self):
        """Connect to the ArduSub vehicle via MAVLink"""
        try:
            # Connect to the vehicle - typically on UDP port 14550
            # This will be the local vehicle when running on BlueOS
            self.mavlink_connection = mavutil.mavlink_connection('udpin:0.0.0.0:14550')
            logger.info("Attempting to connect to ArduSub vehicle...")
            
            # Start connection monitoring thread
            self.running = True
            self.connection_thread = threading.Thread(target=self._monitor_connection)
            self.connection_thread.daemon = True
            self.connection_thread.start()
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to vehicle: {e}")
            return False
    
    def _monitor_connection(self):
        """Monitor the MAVLink connection and heartbeat"""
        while self.running:
            try:
                if self.mavlink_connection:
                    # Wait for heartbeat
                    msg = self.mavlink_connection.recv_match(type='HEARTBEAT', blocking=True, timeout=1.0)
                    if msg:
                        if not self.heartbeat_received:
                            logger.info("Heartbeat received from vehicle!")
                            self.heartbeat_received = True
                        
                        # Update vehicle status
                        self.vehicle_armed = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                        self.vehicle_mode = mavutil.mavlink.enums['MAV_MODE_FLAG'].get(self.vehicle_mode, 'UNKNOWN')
                        
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Connection monitoring error: {e}")
                time.sleep(1.0)
    
    def wait_for_heartbeat(self, timeout=30):
        """Wait for heartbeat from vehicle"""
        start_time = time.time()
        while not self.heartbeat_received and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        return self.heartbeat_received
    
    def arm_vehicle(self):
        """Arm the vehicle"""
        if not self.mavlink_connection or not self.heartbeat_received:
            return False, "No connection to vehicle"
        
        try:
            # Send arm command
            self.mavlink_connection.mav.command_long_send(
                self.mavlink_connection.target_system,
                self.mavlink_connection.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0, 1, 0, 0, 0, 0, 0, 0
            )
            
            # Wait for arm confirmation
            time.sleep(2)
            return self.vehicle_armed, "Vehicle armed successfully" if self.vehicle_armed else "Failed to arm vehicle"
        except Exception as e:
            logger.error(f"Arm command failed: {e}")
            return False, f"Arm command failed: {e}"
    
    def set_mode(self, mode_name):
        """Set vehicle mode (e.g., 'ALT_HOLD')"""
        if not self.mavlink_connection or not self.heartbeat_received:
            return False, "No connection to vehicle"
        
        try:
            # Set mode to ALT_HOLD
            self.mavlink_connection.mav.set_mode_send(
                self.mavlink_connection.target_system,
                mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                self.mavlink_connection.mode_mapping()[mode_name]
            )
            
            time.sleep(1)
            return True, f"Mode set to {mode_name}"
        except Exception as e:
            logger.error(f"Mode change failed: {e}")
            return False, f"Mode change failed: {e}"
    
    def send_movement_command(self, direction, throttle, duration):
        """Send movement command for specified direction, throttle, and duration"""
        if not self.mavlink_connection or not self.heartbeat_received:
            return False, "No connection to vehicle"
        
        try:
            # Calculate movement values based on direction
            forward = 0
            right = 0
            down = 0
            
            if direction == 'up':
                down = -throttle  # Negative for up movement
            elif direction == 'down':
                down = throttle
            elif direction == 'left':
                right = -throttle  # Negative for left movement
            elif direction == 'right':
                right = throttle
            elif direction == 'forward':
                forward = throttle
            elif direction == 'backward':
                forward = -throttle
            
            # Send manual control command
            self.mavlink_connection.mav.manual_control_send(
                self.mavlink_connection.target_system,
                forward,  # Forward/backward
                right,    # Right/left
                down,     # Up/down
                0,        # Yaw
                0         # Button states
            )
            
            # Wait for specified duration
            time.sleep(duration)
            
            # Stop movement
            self.mavlink_connection.mav.manual_control_send(
                self.mavlink_connection.target_system,
                0, 0, 0, 0, 0
            )
            
            return True, f"Movement command executed: {direction} for {duration}s at throttle {throttle}"
        except Exception as e:
            logger.error(f"Movement command failed: {e}")
            return False, f"Movement command failed: {e}"
    
    def set_target_depth(self, depth):
        """Set target depth for the vehicle"""
        if not self.mavlink_connection or not self.heartbeat_received:
            return False, "No connection to vehicle"
        
        try:
            # Send depth command
            self.mavlink_connection.mav.command_long_send(
                self.mavlink_connection.target_system,
                self.mavlink_connection.target_component,
                mavutil.mavlink.MAV_CMD_DO_SET_ROI_LOCATION,
                0, 0, 0, 0, 0, 0, 0, depth
            )
            
            return True, f"Target depth set to {depth} meters"
        except Exception as e:
            logger.error(f"Depth command failed: {e}")
            return False, f"Depth command failed: {e}"
    
    def set_target_heading(self, heading):
        """Set target heading for the vehicle"""
        if not self.mavlink_connection or not self.heartbeat_received:
            return False, "No connection to vehicle"
        
        try:
            # Send heading command
            self.mavlink_connection.mav.command_long_send(
                self.mavlink_connection.target_system,
                self.mavlink_connection.target_component,
                mavutil.mavlink.MAV_CMD_CONDITION_YAW,
                heading,  # Target angle
                25,       # Angular speed (deg/s)
                1,        # Direction (-1:ccw, 1:cw)
                0,        # Relative offset
                0, 0, 0
            )
            
            return True, f"Target heading set to {heading} degrees"
        except Exception as e:
            logger.error(f"Heading command failed: {e}")
            return False, f"Heading command failed: {e}"
    
    def get_status(self):
        """Get current vehicle status"""
        return {
            'connected': self.mavlink_connection is not None,
            'heartbeat': self.heartbeat_received,
            'armed': self.vehicle_armed,
            'mode': self.vehicle_mode
        }
    
    def disconnect(self):
        """Disconnect from vehicle"""
        self.running = False
        if self.connection_thread:
            self.connection_thread.join(timeout=1.0)
        if self.mavlink_connection:
            self.mavlink_connection.close()

# Initialize controller
controller = ArduSubController()

@app.route('/')
def index():
    """Serve the main page"""
    return send_from_directory('static', 'index.html')

@app.route('/api/connect', methods=['POST'])
def connect():
    """Connect to the vehicle"""
    try:
        success = controller.connect_to_vehicle()
        if success:
            return jsonify({'success': True, 'message': 'Connection initiated'})
        else:
            return jsonify({'success': False, 'message': 'Failed to initiate connection'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/status')
def status():
    """Get vehicle status"""
    return jsonify(controller.get_status())

@app.route('/api/wait_heartbeat', methods=['POST'])
def wait_heartbeat():
    """Wait for heartbeat from vehicle"""
    try:
        success = controller.wait_for_heartbeat()
        if success:
            return jsonify({'success': True, 'message': 'Heartbeat received'})
        else:
            return jsonify({'success': False, 'message': 'Timeout waiting for heartbeat'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/arm', methods=['POST'])
def arm():
    """Arm the vehicle"""
    try:
        success, message = controller.arm_vehicle()
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/set_mode', methods=['POST'])
def set_mode():
    """Set vehicle mode"""
    try:
        data = request.get_json()
        mode = data.get('mode', 'ALT_HOLD')
        success, message = controller.set_mode(mode)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/move', methods=['POST'])
def move():
    """Send movement command"""
    try:
        data = request.get_json()
        direction = data.get('direction')
        throttle = data.get('throttle', 0.5)
        duration = data.get('duration', 1.0)
        
        success, message = controller.send_movement_command(direction, throttle, duration)
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/set_depth', methods=['POST'])
def set_depth():
    """Set target depth"""
    try:
        data = request.get_json()
        depth = data.get('depth')
        success, message = controller.set_target_depth(depth)
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/set_heading', methods=['POST'])
def set_heading():
    """Set target heading"""
    try:
        data = request.get_json()
        heading = data.get('heading')
        success, message = controller.set_target_heading(heading)
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from vehicle"""
    try:
        controller.disconnect()
        return jsonify({'success': True, 'message': 'Disconnected from vehicle'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
