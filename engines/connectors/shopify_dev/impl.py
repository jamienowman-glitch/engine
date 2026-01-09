from __future__ import annotations
from typing import Dict, Any
from pydantic import BaseModel, Field

from engines.common.identity import RequestContext
from engines.connectors.generic_stdio.impl import StdioMCPAdapter

# --- Input Models ---

class SearchDocsInput(BaseModel):
    query: str = Field(..., description="The search query for Shopify documentation")

class ValidateLiquidInput(BaseModel):
    code: str = Field(..., description="Liquid code block to validate")

# --- Adapter Instance ---

# We use a singleton adapter to reuse the session if possible, 
# OR we might want to spawn fresh for each call if stability is an issue.
# For Stdio, persistent session is usually better for latency, BUT 
# our `StdioMCPAdapter` implementation (W-10) is stateless (context manager per call).
# This is safer for avoiding zombie processes but slower.
# We will use the stateless approach for now.

_adapter = StdioMCPAdapter(
    command="npx",
    args=["-y", "@shopify/dev-mcp@latest"]
)

# --- Handlers ---

async def search_docs_chunks(ctx: RequestContext, input_data: SearchDocsInput) -> Any:
    # Map input key "query" to what the MCP tool expects.
    # We assume the MCP tool `search_docs_chunks` takes `query`.
    # Based on docs: "search_docs_chunks"
    return await _adapter.call_tool("search_docs_chunks", {"query": input_data.query})

async def validate_theme_codeblocks(ctx: RequestContext, input_data: ValidateLiquidInput) -> Any:
    # Tool: validate_theme_codeblocks
    # Input: likely `code` or similar. 
    # We'll pass the whole dict or map specific fields if we knew the signature.
    # Assuming `code` is correct.
    return await _adapter.call_tool("validate_theme_codeblocks", {"code": input_data.code})
