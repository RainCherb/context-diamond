"""Context Diamond public API."""

from .compressor import CompressionConfig, ContextDiamondCompressor, compress_text
from .model import CapsuleSection, ContextCapsule, Message

__all__ = [
    "CapsuleSection",
    "CompressionConfig",
    "ContextCapsule",
    "ContextDiamondCompressor",
    "Message",
    "compress_text",
]

__version__ = "0.1.0"
