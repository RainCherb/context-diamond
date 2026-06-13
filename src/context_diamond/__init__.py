"""Context Diamond public API."""

from .capsules import diff_capsules, merge_capsules
from .compressor import CompressionConfig, ContextDiamondCompressor, compress_text
from .integrations import compress_documents, compress_messages, compress_tool_payload
from .model import CapsuleSection, ContextCapsule, LossReport, Message
from .plugins import clear_registered_plugins, register_plugin, unregister_plugin
from .profiles import TokenizerProfile, estimate_profile_tokens, list_tokenizer_profiles
from .repo import build_repo_context, compress_repo
from .rerankers import EmbeddingReranker
from .streaming import StreamingCompressor
from .templates import CapsuleTemplate, get_template, list_templates
from .tokenizers import BaseTokenizer, get_tokenizer, list_tokenizers

__all__ = [
    "BaseTokenizer",
    "CapsuleSection",
    "CapsuleTemplate",
    "CompressionConfig",
    "ContextCapsule",
    "ContextDiamondCompressor",
    "EmbeddingReranker",
    "LossReport",
    "Message",
    "StreamingCompressor",
    "build_repo_context",
    "compress_text",
    "compress_documents",
    "compress_messages",
    "compress_repo",
    "compress_tool_payload",
    "clear_registered_plugins",
    "diff_capsules",
    "get_template",
    "get_tokenizer",
    "list_templates",
    "list_tokenizers",
    "merge_capsules",
    "register_plugin",
    "TokenizerProfile",
    "estimate_profile_tokens",
    "list_tokenizer_profiles",
    "unregister_plugin",
]

__version__ = "0.7.0"
