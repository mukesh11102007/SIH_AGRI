"""
Pytest configuration for SmartFarm backend tests.
Runs decision engine tests without requiring a live database or MQTT.
"""
import sys
import os

# Ensure 'backend/' is in the Python path so 'app.*' imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
