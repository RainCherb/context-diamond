from context_diamond import compress_documents, compress_messages, compress_tool_payload

messages = [
    {"role": "user", "content": "Goal: make handoffs cheaper and safer."},
    {"role": "assistant", "content": "Decision: use structured context capsules."},
]

documents = [
    {
        "page_content": "The system must run locally and avoid API keys by default.",
        "metadata": {"source": "product-spec.md"},
    }
]

tool_payload = {
    "tool": "pytest",
    "status": "failed",
    "error": "tests/test_cli.py must include --loss-report coverage",
}

for capsule in (
    compress_messages(messages, token_budget=180),
    compress_documents(documents, token_budget=180),
    compress_tool_payload(tool_payload, token_budget=180),
):
    print(capsule.to_markdown())
