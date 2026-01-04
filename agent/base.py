from abc import ABC, abstractmethod
from pathlib import Path
from agent.config_schema import AgentConfig
import logging

class IPsecBackend(ABC):
    def __init__(self, config: AgentConfig, base_dir: Path, logger: logging.Logger):
        self.config = config
        self.base_dir = base_dir
        self.logger = logger

    @abstractmethod
    def apply_policy(self) -> bool:
        """Applies the IPsec policy. Returns True if successful."""
        pass

    @abstractmethod
    def check_status(self) -> str:
        """Returns 'CONNECTED', 'DISCONNECTED', or 'ERROR'."""
        pass

    @abstractmethod
    def cleanup(self):
        """Removes all policies created by the agent."""
        pass
