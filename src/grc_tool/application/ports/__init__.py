"""Application layer ports (abstract interfaces for external capabilities)."""

from grc_tool.application.ports.agent import AuditAgentPort
from grc_tool.application.ports.sandbox import SandboxPort

__all__ = ["AuditAgentPort", "SandboxPort"]
