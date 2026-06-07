from context_diamond import CompressionConfig, ContextDiamondCompressor

source = """
Goal: reduce token waste during LLM handoffs.
The compressor must run locally and should not require API keys.
Decision: generate a structured capsule instead of a generic summary.
Current state: a CLI and Python API are available.
Open question: should embeddings become an optional reranker?
"""

compressor = ContextDiamondCompressor(CompressionConfig(token_budget=180))
capsule = compressor.compress(source)

print(capsule.to_markdown())
