import sys
import unittest
import os
from pathlib import Path

# Add current directory to path
sys.path.append(os.getcwd())

from agent.config_schema import AgentConfig, load_config, IPsecMode

class TestConfig(unittest.TestCase):
    def test_load_valid_json(self):
        config_path = "config.json"
        config = load_config(config_path)
        # Check first connection
        self.assertTrue(len(config.connections) > 0)
        conn = config.connections[0]
        self.assertEqual(conn.mode, "transport")
        self.assertEqual(conn.auth.type, "psk")
        self.assertEqual(conn.local_subnets[0], "10.0.0.0/24")
        print("\nValid config config.json loaded successfully.")

    def test_invalid_cidr(self):
        # Create a temp invalid config
        bad_json = '{"connections": [{"name": "Bad", "mode": "tunnel", "local_subnets": ["999.999.999.999"], "remote_subnets": ["10.0.0.0/24"], "auth": {"type":"psk","value":"x"}, "encryption": {"ike":"default","esp":"default"}}]}'
        with open("test_bad.json", "w") as f:
            f.write(bad_json)
        
        try:
            with self.assertRaises(ValueError):
                load_config("test_bad.json")
            print("Invalid CIDR rejection verified.")
        finally:
            if os.path.exists("test_bad.json"):
                os.remove("test_bad.json")

    def test_invalid_mode(self):
         bad_json = '{"connections": [{"name": "BadMode", "mode": "magic_carpet", "local_subnets": ["10.0.0.0/24"], "remote_subnets": ["10.0.0.0/24"], "auth": {"type":"psk","value":"x"}, "encryption": {"ike":"default","esp":"default"}}]}'
         with open("test_mode.json", "w") as f:
            f.write(bad_json)
         
         try:
            with self.assertRaises(ValueError):
                load_config("test_mode.json")
            print("Invalid Mode rejection verified.")
         finally:
             if os.path.exists("test_mode.json"):
                os.remove("test_mode.json")

if __name__ == '__main__':
    unittest.main()
