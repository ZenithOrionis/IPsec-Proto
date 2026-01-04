import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from agent.config_schema import AgentConfig, ConnectionConfig, AuthConfig, EncryptionConfig
from agent.platforms.windows import WindowsAgent

class TestWindowsAgent(unittest.TestCase):
    def setUp(self):
        self.config = AgentConfig(
            connections=[
                ConnectionConfig(
                    name="TestWin",
                    mode="tunnel",
                    auth=AuthConfig("psk", "secret"),
                    encryption=EncryptionConfig(ike="aes256-sha256-dh14", esp="aes256gcm16"),
                    local_subnets=["10.0.0.1/32"],
                    remote_subnets=["10.0.0.2/32"],
                    protocol="tcp",
                    local_port="443",
                    remote_port="any"
                )
            ],
            logging_level="info"
        )
        self.logger = MagicMock()
        self.base_dir = Path("C:/Fake/Dir")
        self.agent = WindowsAgent(self.config, self.base_dir, self.logger)

    @patch("agent.platforms.windows.WindowsAgent.run_powershell")
    def test_apply_policy_arguments(self, mock_run_ps):
        mock_run_ps.return_value = True
        
        self.agent.apply_policy()
        
        # Verify run_powershell was called
        self.assertTrue(mock_run_ps.called)
        
        args, kwargs = mock_run_ps.call_args
        script_name = args[0]
        params = args[1]
        
        self.assertEqual(script_name, "apply.ps1")
        
        # Verify Traffic Selectors
        self.assertEqual(params["ConnectionName"], "TestWin")
        self.assertEqual(params["Protocol"], "Tcp")
        self.assertEqual(params["LocalPort"], "443")
        self.assertEqual(params["RemotePort"], "Any")
        
        # Verify Crypto Mapping (aes256 -> AES256, sha256 -> SHA256, dh14 -> DH14)
        self.assertEqual(params["Encryption"], "AES256")
        self.assertEqual(params["Hash"], "SHA256")
        self.assertEqual(params["DHGroup"], "DH14")

if __name__ == '__main__':
    unittest.main()
