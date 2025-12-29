# ENGINES_AGENT_TOUCHPOINTS

Recon of LLM/agent-framework touchpoints (no refactors yet).

| file_path | symbol_or_function | type | notes |
| --- | --- | --- | --- |
| engines/chat/service/llm_client.py | `stream_chat` | Direct LLM call (Vertex Gemini via google-cloud-aiplatform) | Streams chat responses; placeholder prompt assembly; Vertex client init. |
| engines/chat/pipeline.py | pipeline call path to `llm_client.stream_chat` | LLM usage (indirect) | Chat pipeline routes messages to Vertex client; logs to Nexus. |
| engines/orchestration/adapters.py | `AdkRuntimeAdapter`, `BedrockAgentsRuntimeAdapter`, `LangGraphRuntimeAdapter` | Agent runtime clients | Interfaces for ADK/Bedrock/LangGraph runtimes; mappings still stubbed. |
| engines/eval/service.py | `EvalService` + adapters (`VertexEvalAdapter`, `BedrockEvalAdapter`, `RagasEvalAdapter`) | Eval backend clients | Schedules/fetches eval jobs against LLM-based eval services. |
| docs/constitution/ORCHESTRATION_PATTERNS.md | N/A (design) | Agent orchestration design | Contracts for rails + agent/tool calls; planning reference only. |

Candidates for future cleanup: centralize LLM prompts into cards; relocate runtime-specific clients into connectors/core orchestration; ensure Bedrock/ADK/LangGraph clients are injected via connectors, not engines.
