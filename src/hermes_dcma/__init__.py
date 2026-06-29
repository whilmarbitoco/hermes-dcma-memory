from .client import DCMAClient, DCMAError
from .provider import DCMAMemoryProvider

__all__ = [
    "DCMAClient",
    "DCMAError",
    "DCMAMemoryProvider",
    "register",
]


def register() -> DCMAMemoryProvider:
    return DCMAMemoryProvider()
