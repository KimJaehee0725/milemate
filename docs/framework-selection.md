# Framework Selection

## Decision summary
For this project, use the following implementation stack:

- Core agent orchestration: LangGraph
- Model serving: vLLM
- Model: google/gemma-4-26B-A4B-it
- API/backend: FastAPI
- Structured schemas and validation: Pydantic
- Frontend/demo UI: Streamlit first, optional Next.js later
- Retrieval layer: custom adapters + MCP Hub integrations
- State/log storage: SQLite first, optional Postgres later

This means we are not choosing a single monolithic framework for everything.
We are choosing one core orchestration framework and pairing it with simpler supporting tools.

## Why this stack fits the project
The project needs all of the following:
- stage-gated workflow
- human approval checkpoints
- rollback to previous stages
- tool calling
- source-grounded retrieval
- planner-facing output and engineer-facing output
- deterministic enough demo behavior
- local model support through vLLM

Among the frameworks we checked, LangGraph fits this best because it is explicitly oriented toward stateful graph workflows rather than only chat loops or role-playing agents.

## Framework research snapshot
We checked the following candidates using package metadata and repository information.

| Framework | PyPI version checked | GitHub stars checked | Strength | Main weakness for our use case |
|---|---:|---:|---|---|
| LangGraph | 1.1.6 | 29k+ | Strong state graph, checkpoints, workflow control, HITL-friendly | Slightly lower-level than chat-first frameworks |
| PydanticAI | 1.81.0 | 16k+ | Excellent typed outputs, Pythonic ergonomics | Not as naturally centered on rollbackable stage graphs |
| Haystack | 2.27.0 | 24k+ | Strong retrieval pipelines and RAG | More retrieval-centric than workflow-centric |
| AutoGen | 0.7.5 | 57k+ | Strong multi-agent orchestration | Heavier than needed for stage-gated planning MVP |
| CrewAI | 1.14.1 | 48k+ | Easy role-based agent composition | Better for agent-team demos than explicit stage state machines |
| smolagents | 1.24.0 | 26k+ | Lightweight and flexible | Better for tool/code agents than structured stage workflow |

## Final recommendation
### 1. Core workflow framework: LangGraph
Use LangGraph as the main orchestration layer.

Why:
- Our project is naturally a graph/state problem, not just a prompt chaining problem.
- Stage 1 -> Stage 2 -> Stage 3 -> Stage 4 is already a graph.
- Human approval and rollback are first-class architectural concerns for us.
- We need stage state, not just conversation history.
- We may later add branching logic by scenario type.

LangGraph is the best fit for:
- stage nodes
- approval checkpoints
- rollback edges
- persistent state
- verifier subgraph
- future scenario branching

How to use it in our architecture:
- one graph for the common stage engine
- scenario-specific prompt overlays loaded from config
- verifier node before finalization
- rollback edges from stage 3 and stage 4 to earlier stages
- state object containing
  - selected scenario
  - current stage
  - approved stages
  - decision log
  - unresolved questions
  - citations

### 2. Backend framework: FastAPI
Use FastAPI as the API layer around the graph.

Why:
- easy Python integration
- clean request/response contracts
- good fit with Pydantic models
- easy frontend/backend separation for a 4-person team
- works well with local vLLM deployments

FastAPI should handle:
- session creation
- stage submission
- stage approval
- rollback request
- final report retrieval

### 3. Validation layer: Pydantic, not full PydanticAI as the core
Use Pydantic models directly for schemas and validation.

Why:
- we already need strict stage schemas
- FastAPI uses Pydantic naturally
- this avoids unnecessary framework overlap
- PydanticAI is attractive, but our main bottleneck is workflow/state management, not typed agent ergonomics

Where Pydantic should be used:
- stage response schema
- decision log schema
- citation schema
- planner report schema
- engineer report schema

Note:
PydanticAI is still a reasonable optional helper later if we want typed model wrappers, but it should not be the primary orchestration framework for this project.

### 4. Retrieval approach: custom adapters + MCP Hub, not Haystack as the core
Do not make Haystack the center of the system.

Why:
- our retrieval needs are real, but the project is not primarily a retrieval framework demo
- most of our complexity lies in stage logic, human-in-the-loop flow, and verifier behavior
- we already have a clear external-source plan through MCP Hub + markdown knowledge base

Recommended retrieval stack:
- custom retrieval adapters in Python
- MCP Hub integrations for web search / GitHub / fetch / filesystem / memory
- local markdown knowledge base
- legalize-kr integration for Korean laws

Haystack can still be used later if retrieval complexity grows, but it should not be the first framework we introduce.

### 5. Frontend choice: Streamlit first
Use Streamlit first for the working prototype.

Why:
- fastest path to a usable stage UI
- easy form-driven interaction for stage approval/edit/rollback
- simple for a research/demo prototype
- Python-only stack reduces coordination overhead

Use Streamlit for:
- stage progression view
- approve/edit buttons
- rollback control
- planner/engineer report rendering
- scenario selector

If the team later wants a cleaner product-style UI, Next.js can be considered after the MVP is stable.

## Why we are not choosing the other frameworks as the core
### Why not AutoGen?
AutoGen is powerful, but our MVP is not fundamentally a multi-agent conversation system.
Our main need is a controlled stage machine with explicit approval and rollback.
AutoGen is stronger when the main story is autonomous agent-team interaction.
That is not the core of this project.

### Why not CrewAI?
CrewAI is good for role-based task orchestration, but our architecture is better expressed as a state graph than as a crew of roles.
It may be nice for presentation, but it is not the most direct implementation match.

### Why not Haystack?
Haystack is excellent for retrieval pipelines, but retrieval is only one part of our system.
If we choose Haystack as the core, the system may become retrieval-centric rather than workflow-centric.

### Why not smolagents?
smolagents is lightweight and interesting, but we need more explicit stage control, rollback semantics, and state handling than it naturally emphasizes.

### Why not PydanticAI as the main framework?
PydanticAI is elegant and Pythonic, especially for typed outputs.
However, our highest-priority problem is not just output typing.
It is stage management, human approval, and rollbackable workflow.
That makes LangGraph the better primary framework.

## vLLM and Gemma integration plan
The model will be served locally with vLLM.
The important implementation point is to expose vLLM through an OpenAI-compatible API endpoint.

Recommended architecture:
- vLLM serves `google/gemma-4-26B-A4B-it`
- backend uses an OpenAI-compatible client against the local base URL
- LangGraph nodes call the local endpoint through a model wrapper

This is important because it keeps the framework choice flexible.
We do not need a framework with special Gemma-only support.
We need a framework that works well with OpenAI-compatible endpoints.

## Concrete architecture decision
### Chosen stack
- LangGraph for stage workflow orchestration
- FastAPI for backend APIs
- Pydantic for schemas
- Streamlit for UI
- vLLM for local inference
- MCP Hub + custom adapters for retrieval
- SQLite for state during MVP

### Internal module mapping
- Module A: Streamlit UI
- Module B: FastAPI + LangGraph + stage manager
- Module C: MCP adapters + knowledge base + legalize-kr + source retrieval
- Module D: prompts + verifier + evaluation

## What the first implementation milestone should look like
The first integrated milestone should be:
- Streamlit frontend with stage 1~4 screens
- FastAPI backend wrapping a LangGraph workflow
- one working scenario: dynamic dispatch
- one retrieval path using local knowledge + fetch/github adapter
- one verifier node
- planner report + engineer report + decision log

Do not begin with:
- multi-agent teams
- advanced long-term memory
- multiple retrieval frameworks at once
- a heavy JS frontend

## Decision
Primary framework decision:
- Choose LangGraph as the core framework.

Supporting framework decisions:
- Choose FastAPI for the backend API.
- Choose Pydantic for validation and schemas.
- Choose Streamlit for the first frontend prototype.
- Keep retrieval lightweight and modular through MCP Hub + adapters.

## Implementation note for the repo
The current repository structure and YAML config already fit this decision well.
What should happen next is:
1. implement the LangGraph state model
2. connect FastAPI routes to the stage graph
3. wire Streamlit to those APIs
4. connect local vLLM endpoint
5. add retrieval adapters and verifier
