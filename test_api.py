import unittest
import threading
import time
import urllib.request
import json
import logging
from agent.core import IPsecAgent, AgentState
from agent.config_schema import AgentConfig, ConnectionConfig, AuthConfig, EncryptionConfig

class TestHealthAPI(unittest.TestCase):
    def test_api_status(self):
        # Setup Mock Agent with config
        conn = ConnectionConfig(
            name="TestAPI", mode="tunnel", 
            auth=AuthConfig("psk", "x"), 
            encryption=EncryptionConfig("default", "default"),
            local_subnets=["10.0.0.0/24"], remote_subnets=["192.168.1.0/24"]
        )
        config = AgentConfig(
            connections=[conn], 
            logging_level="info", 
            api_port=9999, # Test port
            logging_type="stdout" 
        )
        
        agent = IPsecAgent("dummy_path")
        agent.config = config
        agent.state = AgentState.CONNECTED
        
        # Mock check_status
        agent.check_status = lambda: "CONNECTED"
        
        # Start API
        # We need to ensure we don't blocking-wait 
        agent.logger = logging.getLogger("TestAPI")
        agent.start_health_api()
        
        time.sleep(1) # Wait for startup
        
        try:
            with urllib.request.urlopen("http://localhost:9999/status") as response:
                data = json.loads(response.read().decode())
                print(f"\nAPI Response: {data}")
                self.assertEqual(data["status"], "CONNECTED")
                self.assertEqual(data["agent_state"], "CONNECTED")
        except Exception as e:
            self.fail(f"API request failed: {e}")

if __name__ == '__main__':
    unittest.main()
