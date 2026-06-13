"""Context Diamond public API."""

from .capsules import diff_capsules, merge_capsules
from .compressor import CompressionConfig, ContextDiamondCompressor, compress_text
from .integrations import compress_documents, compress_messages, compress_tool_payload
from .model import CapsuleSection, ContextCapsule, LossReport, Message
from .plugins import clear_registered_plugins, register_plugin, unregister_plugin
from .profiles import TokenizerProfile, estimate_profile_tokens, list_tokenizer_profiles
from .repo import build_repo_context, compress_repo
from .rerankers import EmbeddingReranker

__all__ = [
    "CapsuleSection",
    "CompressionConfig",
    "ContextCapsule",
    "ContextDiamondCompressor",
    "EmbeddingReranker",
    "LossReport",
    "Message",
    "build_repo_context",
    "compress_text",
    "compress_documents",
    "compress_messages",
    "compress_repo",
    "compress_tool_payload",
    "clear_registered_plugins",
    "diff_capsules",
    "merge_capsules",
    "register_plugin",
    "TokenizerProfile",
    "estimate_profile_tokens",
    "list_tokenizer_profiles",
    "unregister_plugin",
]

__version__ = "0.6.3"
