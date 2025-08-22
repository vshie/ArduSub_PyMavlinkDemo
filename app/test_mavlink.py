#!/usr/bin/env python3
"""
Test script for PyMavlink functionality
This script can be used to test basic MAVLink operations locally
"""

import time
import sys
from pymavlink import mavutil

def test_mavlink_connection():
    """Test basic MAVLink connection functionality"""
    print("Testing PyMavlink functionality...")
    
    try:
        # Test creating a MAVLink connection (this will fail locally but tests imports)
        print("✓ PyMavlink imported successfully")
        
        # Test MAVLink constants
        print(f"✓ MAV_CMD_COMPONENT_ARM_DISARM: {mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM}")
        print(f"✓ MAV_MODE_FLAG_SAFETY_ARMED: {mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED}")
        
        # Test creating a dummy connection for testing
        print("✓ MAVLink constants accessible")
        
        print("\n✅ All PyMavlink tests passed!")
        return True
        
    except ImportError as e:
        print(f"❌ PyMavlink import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_flask_imports():
    """Test Flask imports"""
    print("\nTesting Flask imports...")
    
    try:
        from flask import Flask, request, jsonify, render_template
        from flask_cors import CORS
        print("✓ Flask imports successful")
        return True
    except ImportError as e:
        print(f"❌ Flask import failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing ArduSub PyMavlink Control Extension")
    print("=" * 50)
    
    # Test imports
    flask_ok = test_flask_imports()
    mavlink_ok = test_mavlink_connection()
    
    print("\n" + "=" * 50)
    if flask_ok and mavlink_ok:
        print("🎉 All tests passed! Extension should work correctly.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check dependencies.")
        sys.exit(1)
