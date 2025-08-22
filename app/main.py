#!/usr/bin/env python3

import time
import logging
import threading
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymavlink import mavutil
from pymavlink.quaternion import QuaternionBase
import math
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
        self.boot_time = time.time()  # Track boot time for MAVLink messages
        
        # Mavlink2Rest configuration
        self.mavlink2rest_url = "http://host.docker.internal/mavlink2rest/mavlink"
        
        # Constants
        self.ALT_HOLD_MODE = 2
        
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
                        
                        # Update vehicle status using proper bitmask
                        self.vehicle_armed = bool(msg.base_mode & 0b10000000)  # MAV_MODE_FLAG_SAFETY_ARMED
                        self.vehicle_mode = msg.custom_mode
                        
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
    
    def is_armed(self):
        """Check if vehicle is armed using proper bitmask"""
        try:
            if self.mavlink_connection:
                heartbeat = self.mavlink_connection.wait_heartbeat()
                return bool(heartbeat.base_mode & 0b10000000)
            return False
        except:
            return False
    
    def mode_is(self, mode):
        """Check if vehicle is in specific mode"""
        try:
            if self.mavlink_connection:
                heartbeat = self.mavlink_connection.wait_heartbeat()
                return bool(heartbeat.custom_mode == mode)
            return False
        except:
            return False
    
    def arm_vehicle(self):
        """Arm the vehicle"""
        if not self.mavlink_connection or not self.heartbeat_received:
            return False, "No connection to vehicle"
        
        try:
            # Use the proper arming method
            self.mavlink_connection.arducopter_arm()
            
            # Wait for arm confirmation
            time.sleep(2)
            armed = self.is_armed()
            return armed, "Vehicle armed successfully" if armed else "Failed to arm vehicle"
        except Exception as e:
            logger.error(f"Arm command failed: {e}")
            return False, f"Arm command failed: {e}"
    
    def set_mode(self, mode_name):
        """Set vehicle mode (e.g., 'ALT_HOLD')"""
        if not self.mavlink_connection or not self.heartbeat_received:
            return False, "No connection to vehicle"
        
        try:
            # Set mode using proper method
            self.mavlink_connection.set_mode('ALT_HOLD')
            
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
        """Set target depth for the vehicle using proper MAVLink command
        Based on official ArduSub documentation
        """
        if not self.mavlink_connection or not self.heartbeat_received:
            return False, "No connection to vehicle"
        
        try:
            # Use set_position_target_global_int_send for depth control
            # Based on the official ArduSub documentation
            self.mavlink_connection.mav.set_position_target_global_int_send(
                int(1e3 * (time.time() - self.boot_time)),  # ms since boot
                self.mavlink_connection.target_system, 
                self.mavlink_connection.target_component,
                coordinate_frame=mavutil.mavlink.MAV_FRAME_GLOBAL_INT,
                type_mask=( # ignore everything except z position
                    mavutil.mavlink.POSITION_TARGET_TYPEMASK_X_IGNORE |
                    mavutil.mavlink.POSITION_TARGET_TYPEMASK_Y_IGNORE |
                    # DON'T mavutil.mavlink.POSITION_TARGET_TYPEMASK_Z_IGNORE |
                    mavutil.mavlink.POSITION_TARGET_TYPEMASK_VX_IGNORE |
                    mavutil.mavlink.POSITION_TARGET_TYPEMASK_VY_IGNORE |
                    mavutil.mavlink.POSITION_TARGET_TYPEMASK_VZ_IGNORE |
                    mavutil.mavlink.POSITION_TARGET_TYPEMASK_AX_IGNORE |
                    mavutil.mavlink.POSITION_TARGET_TYPEMASK_AY_IGNORE |
                    mavutil.mavlink.POSITION_TARGET_TYPEMASK_AZ_IGNORE |
                    # DON'T mavutil.mavlink.POSITION_TARGET_TYPEMASK_FORCE_SET |
                    mavutil.mavlink.POSITION_TARGET_TYPEMASK_YAW_IGNORE |
                    mavutil.mavlink.POSITION_TARGET_TYPEMASK_YAW_RATE_IGNORE
                ), 
                lat_int=0, lon_int=0, alt=depth,  # (x, y WGS84 frame pos - not used), z [m]
                vx=0, vy=0, vz=0,  # velocities in NED frame [m/s] (not used)
                afx=0, afy=0, afz=0, yaw=0, yaw_rate=0
                # accelerations in NED frame [N], yaw, yaw_rate
                #  (all not supported yet, ignored in GCS Mavlink)
            )
            
            return True, f"Target depth set to {depth} meters"
        except Exception as e:
            logger.error(f"Depth command failed: {e}")
            return False, f"Depth command failed: {e}"
    
    def set_target_attitude(self, roll, pitch, yaw):
        """Set target attitude while in depth-hold mode
        Based on official ArduSub documentation
        """
        if not self.mavlink_connection or not self.heartbeat_received:
            return False, "No connection to vehicle"
        
        # Only allow attitude control in ALT_HOLD mode
        if not self.mode_is(self.ALT_HOLD_MODE):
            return False, "Attitude control only available in ALT_HOLD mode"
        
        try:
            # Use set_attitude_target_send for attitude control
            # Based on the official ArduSub documentation
            self.mavlink_connection.mav.set_attitude_target_send(
                int(1e3 * (time.time() - self.boot_time)),  # ms since boot
                self.mavlink_connection.target_system, 
                self.mavlink_connection.target_component,
                # allow throttle to be controlled by depth_hold mode
                mavutil.mavlink.ATTITUDE_TARGET_TYPEMASK_THROTTLE_IGNORE,
                # -> attitude quaternion (w, x, y, z | zero-rotation is 1, 0, 0, 0)
                QuaternionBase([math.radians(angle) for angle in (roll, pitch, yaw)]),
                0, 0, 0, 0  # roll rate, pitch rate, yaw rate, thrust
            )
            
            return True, f"Target attitude set to roll={roll}°, pitch={pitch}°, yaw={yaw}°"
        except Exception as e:
            logger.error(f"Attitude command failed: {e}")
            return False, f"Attitude command failed: {e}"
    
    def set_target_heading(self, heading):
        """Set target heading for the vehicle using proper MAVLink command"""
        if not self.mavlink_connection or not self.heartbeat_received:
            return False, "No connection to vehicle"
        
        # Only allow heading control in ALT_HOLD mode
        if not self.mode_is(self.ALT_HOLD_MODE):
            return False, "Heading control only available in ALT_HOLD mode"
        
        try:
            # Use set_attitude_target_send for heading control (yaw only)
            # Based on the official ArduSub documentation
            self.mavlink_connection.mav.set_attitude_target_send(
                int(1e3 * (time.time() - self.boot_time)),  # ms since boot
                self.mavlink_connection.target_system, 
                self.mavlink_connection.target_component,
                # allow throttle to be controlled by depth_hold mode
                mavutil.mavlink.ATTITUDE_TARGET_TYPEMASK_THROTTLE_IGNORE,
                # -> attitude quaternion (w, x, y, z | zero-rotation is 1, 0, 0, 0)
                QuaternionBase([0, 0, math.radians(heading)]),  # roll=0, pitch=0, yaw=heading
                0, 0, 0, 0  # roll rate, pitch rate, yaw rate, thrust
            )
            
            return True, f"Target heading set to {heading} degrees"
        except Exception as e:
            logger.error(f"Heading command failed: {e}")
            return False, f"Heading command failed: {e}"
    
    def get_vehicle_metrics(self):
        """Get real-time vehicle metrics using Mavlink2Rest"""
        try:
            # Get vehicle arm state
            arm_response = requests.get(f"{self.mavlink2rest_url}/vehicles/1/components/1/HEARTBEAT", timeout=2)
            if arm_response.status_code == 200:
                arm_data = arm_response.json()
                armed = bool(arm_data.get('message', {}).get('base_mode', 0) & 0x80)  # MAV_MODE_FLAG_SAFETY_ARMED
            else:
                armed = False
            
            # Get current depth
            depth_response = requests.get(f"{self.mavlink2rest_url}/vehicles/1/components/1/VFR_HUD", timeout=2)
            if depth_response.status_code == 200:
                depth_data = depth_response.json()
                current_depth = depth_data.get('message', {}).get('alt', 0)
            else:
                current_depth = 0
            
            # Get current heading
            heading_response = requests.get(f"{self.mavlink2rest_url}/vehicles/1/components/1/VFR_HUD", timeout=2)
            if heading_response.status_code == 200:
                heading_data = heading_response.json()
                current_heading = heading_data.get('message', {}).get('heading', 0)
            else:
                current_heading = 0
            
            # Get vehicle mode
            mode_response = requests.get(f"{self.mavlink2rest_url}/vehicles/1/components/1/HEARTBEAT", timeout=2)
            if mode_response.status_code == 200:
                mode_data = mode_response.json()
                custom_mode = mode_data.get('message', {}).get('custom_mode', 0)
                # Map custom mode to readable mode name
                mode_name = self._get_mode_name(custom_mode)
            else:
                mode_name = "Unknown"
            
            return {
                'armed': armed,
                'current_depth': round(current_depth, 2),
                'current_heading': int(current_heading),
                'mode': mode_name,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Failed to get vehicle metrics: {e}")
            return {
                'armed': False,
                'current_depth': 0,
                'current_heading': 0,
                'mode': "Unknown",
                'timestamp': time.time()
            }
    
    def _get_mode_name(self, custom_mode):
        """Convert custom mode number to readable mode name"""
        # Common ArduSub modes
        mode_mapping = {
            0: "MANUAL",
            1: "STABILIZE", 
            2: "ALT_HOLD",
            3: "AUTO",
            4: "GUIDED",
            5: "LOITER",
            6: "RTL",
            7: "CIRCLE",
            8: "POSITION",
            9: "LAND",
            10: "OF_LOITER",
            11: "DRIFT",
            13: "SPORT",
            14: "FLIP",
            15: "AUTOTUNE",
            16: "POSHOLD",
            17: "BRAKE",
            18: "THROW",
            19: "AVOID_ADSB",
            20: "GUIDED_NOGPS",
            21: "SMART_RTL",
            22: "FLOWHOLD",
            23: "FOLLOW",
            24: "ZIGZAG",
            25: "SYSTEMID",
            26: "AUTOROTATE",
            27: "AUTO_RTL"
        }
        return mode_mapping.get(custom_mode, f"Mode_{custom_mode}")
    
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

@app.route('/api/vehicle_metrics')
def vehicle_metrics():
    """Get real-time vehicle metrics via Mavlink2Rest"""
    try:
        metrics = controller.get_vehicle_metrics()
        return jsonify({'success': True, 'data': metrics})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

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

@app.route('/api/set_attitude', methods=['POST'])
def set_attitude():
    """Set target attitude (roll, pitch, yaw)"""
    try:
        data = request.get_json()
        roll = data.get('roll', 0)
        pitch = data.get('pitch', 0)
        yaw = data.get('yaw', 0)
        success, message = controller.set_target_attitude(roll, pitch, yaw)
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
    port = int(os.environ.get('FLASK_RUN_PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
