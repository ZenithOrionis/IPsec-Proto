import unittest
import shutil
from pathlib import Path
from agent.config_schema import AgentConfig, AuthConfig, EncryptionConfig
from agent.platforms.linux import LinuxAgent
import logging

class TestLinuxAgent(unittest.TestCase):
    def setUp(self):
        self.base_dir = Path("test_output").resolve()
        self.base_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger("TestLinux")
        
        from agent.config_schema import ConnectionConfig
        conn = ConnectionConfig(
            name="TestConn",
            mode="tunnel",
            ike_version="ikev2",
            auth=AuthConfig(type="psk", value="TestSecret"),
            encryption=EncryptionConfig(ike="aes256-sha256-modp2048", esp="aes256gcm128"),
            local_subnets=["10.0.0.0/24"],
            remote_subnets=["192.168.1.0/24"],
            protocol="tcp",
            local_port="80",
            remote_port="any",
            lifetime_minutes=60
        )

        self.config = AgentConfig(
            connections=[conn],
            logging_level="info"
        )

    def tearDown(self):
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)

    def test_generate_swanctl_conf(self):
        agent = LinuxAgent(self.config, self.base_dir, self.logger)
        conf = agent._generate_swanctl_conf()
        
        print("\nGenerated Config:\n" + conf)
        
        self.assertIn("connections {", conf)
        self.assertIn("local_addrs = 10.0.0.0", conf)
        self.assertIn("remote_addrs = 192.168.1.0", conf)
        self.assertIn("proposals = aes256-sha256-modp2048", conf)
        self.assertIn("esp_proposals = aes256gcm128", conf)
        self.assertIn('secret = "TestSecret"', conf)
        # Check traffic selector with port
        self.assertIn("[tcp/80]", conf)

if __name__ == '__main__':
    unittest.main()
