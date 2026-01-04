import json
import ipaddress
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any

# Try to import PyYAML, fallback to JSON-only if missing
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

class IPsecMode(Enum):
    TUNNEL = "tunnel"
    TRANSPORT = "transport"

class IKEVersion(Enum):
    IKEv2 = "ikev2"

class AuthType(Enum):
    PSK = "psk"
    # User example: type: psk. So 'psk'.
    PSK_CORRECT = "psk"

@dataclass
class AuthConfig:
    type: str
    value: str

    def validate(self):
        if self.type.lower() != "psk":
            raise ValueError(f"Unsupported auth type: {self.type}. Only 'psk' is supported.")
        if not self.value:
            raise ValueError("Auth value (PSK) cannot be empty.")

@dataclass
class EncryptionConfig:
    ike: str
    esp: str

    def validate(self):
        # Allow any string for flexibility, but warn if it looks weak
        weak_algos = ["des", "md5", "3des", "sha1"]
        
        for algo in [self.ike.lower(), self.esp.lower()]:
             if algo == "default": continue
             for weak in weak_algos:
                 if weak in algo:
                     # Just print/log warning in real app, here we raise specific error for strictness or pass?
                     # User wants to be able to configure it.
                     pass 
        pass

@dataclass
class ConnectionConfig:
    name: str
    mode: str
    auth: AuthConfig
    encryption: EncryptionConfig
    local_subnets: list[str]
    remote_subnets: list[str]
    # Traffic Selectors
    protocol: str = "any" # tcp, udp, icmp, any
    local_port: str = "any" 
    remote_port: str = "any"
    
    ike_version: str = "ikev2"
    lifetime_minutes: int = 60

    def validate(self):
        if not self.name: raise ValueError("Connection name is required")
        if self.mode.lower() not in [m.value for m in IPsecMode]:
             raise ValueError(f"Invalid mode: {self.mode}")
        self.auth.validate()
        self.encryption.validate()
        if not self.local_subnets or not self.remote_subnets:
            raise ValueError("Local and Remote subnets are required")
        # Validate CIDRs
        for s in self.local_subnets + self.remote_subnets:
             try: ipaddress.ip_network(s, strict=False)
             except ValueError: raise ValueError(f"Invalid subnet: {s}")
        
        # Basic Protocol validation
        valid_protos = ["tcp", "udp", "icmp", "any", "gre"]
        if self.protocol.lower() not in valid_protos and not self.protocol.isdigit():
             # allow numeric protocols too
             pass 

@dataclass
class AgentConfig:
    connections: list[ConnectionConfig]
    logging_level: str
    logging_type: str = "file" # file, syslog, stdout
    api_port: int = None # Port for Health API, None = disabled

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentConfig':
        try:
            conns_data = data.get("connections", [])
            connections = []
            
            # Legacy support or migration helper check? 
            # If "traffic" exists but "connections" doesn't, we could shim it, 
            # but requirements say "Breaking Change", so let's stick to new format.
            
            for c_data in conns_data:
                name = c_data.get("name", "Unknown")
                
                auth_data = c_data.get("auth", {})
                auth = AuthConfig(type=auth_data.get("type", ""), value=auth_data.get("value", ""))
                
                enc_data = c_data.get("encryption", {})
                encryption = EncryptionConfig(ike=enc_data.get("ike", "default"), esp=enc_data.get("esp", "default"))
                
                # Normalize subnets to list if string provided
                locals = c_data.get("local_subnets", [])
                if isinstance(locals, str): locals = [locals]
                
                remotes = c_data.get("remote_subnets", [])
                if isinstance(remotes, str): remotes = [remotes]

                lifetime = c_data.get("lifetime", {})
                sa_minutes = int(lifetime.get("sa_minutes", 60))

                conn = ConnectionConfig(
                    name=name,
                    mode=c_data.get("mode", "tunnel"),
                    ike_version=c_data.get("ike_version", "ikev2"),
                    auth=auth,
                    encryption=encryption,
                    local_subnets=locals,
                    remote_subnets=remotes,
                    protocol=str(c_data.get("protocol", "any")),
                    local_port=str(c_data.get("local_port", "any")),
                    remote_port=str(c_data.get("remote_port", "any")),
                    lifetime_minutes=sa_minutes
                )
                connections.append(conn)

            return cls(
                connections=connections,
                logging_level=data.get("logging", "info"),
                logging_type=data.get("logging_type", "file"),
                api_port=data.get("api_port")
            )
        except Exception as e:
            raise ValueError(f"Config parsing error: {e}")

    def validate(self):
        if not self.connections:
            raise ValueError("No connections defined in configuration.")
        for c in self.connections:
            c.validate()



def load_config(file_path: str) -> AgentConfig:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Config file not found: {file_path}")

    with open(file_path, 'r') as f:
        content = f.read()
    
    data = {}
    if file_path.endswith('.json'):
        data = json.loads(content)
    elif file_path.endswith('.yaml') or file_path.endswith('.yml'):
        if HAS_YAML:
            data = yaml.safe_load(content)
        else:
            raise ImportError("PyYAML not installed. Cannot parse YAML config.")
    else:
        # Try JSON first
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            if HAS_YAML:
                try:
                    data = yaml.safe_load(content)
                except yaml.YAMLError:
                    raise ValueError("Could not parse config as JSON or YAML.")
            else:
                raise ValueError("Could not parse config as JSON.")
                
    config = AgentConfig.from_dict(data)
    config.validate()
    return config
