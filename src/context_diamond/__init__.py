"""Context Diamond public API."""

from .compressor import CompressionConfig, ContextDiamondCompressor, compress_text
from .integrations import compress_documents, compress_messages, compress_tool_payload
from .model import CapsuleSection, ContextCapsule, LossReport, Message
from .profiles import TokenizerProfile, estimate_profile_tokens, list_tokenizer_profiles

__all__ = [
    "CapsuleSection",
    "CompressionConfig",
    "ContextCapsule",
    "ContextDiamondCompressor",
    "LossReport",
    "Message",
    "compress_text",
    "compress_documents",
    "compress_messages",
    "compress_tool_payload",
    "TokenizerProfile",
    "estimate_profile_tokens",
    "list_tokenizer_profiles",
]

__version__ = "0.1.0"
