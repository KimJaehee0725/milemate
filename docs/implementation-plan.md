# Last-Mile Planning Agent Implementation Plan

> For Hermes: This is a project execution plan for a 4-person team. Use it as the source of truth for implementation sequencing, ownership, and integration.

Goal: Build a stage-gated, human-in-the-loop planning agent that helps planners structure last-mile service ideas, identify enabling technologies, and produce planner-facing and engineer-facing outputs.

Architecture: The system will be built as a modular prototype with four separable layers: frontend interaction layer, orchestration/backend layer, knowledge/data layer, and evaluation/demo layer. The first demo will use the dynamic dispatch scenario, but the framework must support ETA prediction and failed-delivery risk scenarios with the same stage workflow.

Tech Stack: Python backend, FastAPI API server, simple frontend (Streamlit or Next.js), vector/database layer, local markdown knowledge base, MCP integrations via mcp-hub, and optional lightweight SQLite/Postgres for logs and stage state.

---

## 0. What the team is actually building

The prototype should support the following minimum user flow:
1. User enters a last-mile service idea.
2. Agent classifies the idea into a scenario type.
3. Agent runs stage 1 and proposes problem definition, KPI candidates, and scope candidates.
4. User approves or edits stage 1.
5. Agent runs stage 2 and proposes feature structure and MVP scope.
6. User approves or edits stage 2.
7. Agent runs stage 3 and verifies data/technical/regulatory feasibility.
8. User approves or sends the workflow back to an earlier stage.
9. Agent generates stage 4 outputs:
   - planner report
   - engineer report
   - decision log

The first milestone does not need full production-grade agent autonomy. It only needs a convincing, modular prototype that clearly demonstrates:
- stage-gated progression
- human approval checkpoints
- rollback to earlier stages
- retrieval + web/document search
- memory of prior stage decisions
- verifier pass before final output

## 1. Module breakdown for 4 team members

The system is split into 4 modules so each team member can work mostly independently.

### Module A. Product UX and Stage Workflow
Owner: Team Member 1

Objective: Design and implement the planner-facing interaction flow.

Responsibilities:
- Define stage UI and user actions
- Implement stage approval / reject / rollback controls
- Build demo flow for 3 scenarios
- Define final report layout for planner and engineer outputs

Primary outputs:
- wireframes
- frontend screens
- stage transition UX
- demo script alignment

Dependencies:
- needs API contract from Module B
- needs scenario templates from Module D
- can start before retrieval/MCP implementation is complete by using mock responses

### Module B. Agent Orchestration Backend
Owner: Team Member 2

Objective: Build the central backend that manages stage state, calls retrieval/tools, and produces structured outputs.

Responsibilities:
- FastAPI server or equivalent backend
- stage state machine implementation
- orchestration logic for stage 1~4
- short-term memory/session state
- decision log generation
- rollback logic
- output schema enforcement

Primary outputs:
- backend API
- stage manager
- orchestration service
- response schemas

Dependencies:
- needs prompt/templates from Module D
- needs retrieval interfaces from Module C
- can be developed with mocked retrieval adapters at first

### Module C. Knowledge, Retrieval, and MCP Integrations
Owner: Team Member 3

Objective: Build the external knowledge pipeline and MCP-compatible retrieval layer.

Responsibilities:
- organize markdown knowledge base
- connect mcp-hub candidates where possible
- build retrieval adapters for papers, docs, GitHub repos, legal sources
- prepare legalize-kr workflow for Korean law lookup
- implement citation/source tracking

Primary outputs:
- source inventory
- retrieval adapter layer
- local knowledge base structure
- mcp-hub config draft
- citation format for outputs

Dependencies:
- can progress independently early
- must provide APIs or mock interfaces to Module B
- must align source categories with Module D evaluation needs

### Module D. Scenario Design, Prompts, Verification, and Evaluation
Owner: Team Member 4

Objective: Define the intelligence layer: scenario templates, prompts, verifier logic, and evaluation/demo assets.

Responsibilities:
- create prompt templates for stage 1~4
- define scenario-specific variations for 3 scenarios
- design verifier checklists
- define evaluation rubric
- prepare sample inputs, expected outputs, and demo dataset

Primary outputs:
- prompt library
- verifier rule set
- scenario templates
- evaluation checklist
- demo examples

Dependencies:
- works with all modules but can begin immediately
- should coordinate closely with Module B for structured output schemas

## 2. Recommended repository structure

Use this structure so work can be split cleanly.

```text
project-root/
  README.md
  docs/
    project-overview.md
    last-mile-service-options.md
    implementation-plan.md
  app/
    frontend/
      pages/
      components/
      stage_views/
    backend/
      main.py
      api/
        routes_stage.py
        routes_session.py
        routes_report.py
      core/
        orchestrator.py
        stage_manager.py
        rollback_manager.py
        schemas.py
      services/
        planner_service.py
        verifier_service.py
        report_service.py
        memory_service.py
      integrations/
        retrieval_adapter.py
        mcp_adapter.py
        github_adapter.py
        legal_adapter.py
        web_search_adapter.py
  knowledge/
    papers/
    docs/
    cases/
    laws/
    datasets/
    patents/
  prompts/
    common/
      system.md
      stage_1.md
      stage_2.md
      stage_3.md
      stage_4.md
    scenarios/
      dispatch.md
      eta.md
      failed_delivery.md
  data/
    demo_inputs/
    demo_outputs/
    synthetic/
  tests/
    test_stage_manager.py
    test_verifier.py
    test_report_schema.py
    test_retrieval_adapters.py
  config/
    app.example.yaml
    mcphub.example.json
```

## 3. Build order

Do not try to build everything at once. Build in this order.

### Phase 1. Freeze the contracts
Objective: Agree on interfaces before implementation diverges.

Deliverables:
- stage definitions
- output schema
- API contract between frontend and backend
- source categories for retrieval
- scenario template schema

Who leads:
- Module B + Module D
n
Must decide now:
- frontend framework: Streamlit or Next.js
- backend framework: FastAPI recommended
- state storage: in-memory + JSON for MVP, or SQLite if needed
- output format: strict JSON internally, rendered markdown externally

### Phase 2. Build a mocked end-to-end vertical slice
Objective: Get one full path working before real retrieval is added.

Scope:
- one scenario only: dynamic dispatch
- mocked retrieval
- mocked verifier
- real stage approval UI
- real rollback flow

Who leads:
- Module A + Module B

Success criteria:
- user can complete stage 1~4 in the UI
- rollback works
- planner report and engineer report render correctly

### Phase 3. Replace mocks with real retrieval and knowledge access
Objective: Make the system grounded.

Scope:
- local markdown knowledge base
- web/document retrieval adapters
- legalize-kr law lookup
- source citation display

Who leads:
- Module C, supported by Module B

Success criteria:
- output includes cited sources
- at least one legal source, one technical source, and one scenario source can be retrieved

### Phase 4. Add verifier and scenario generalization
Objective: Show that the framework is reusable across scenarios.

Scope:
- implement stage 3 verifier rules
- add ETA and failed-delivery scenario templates
- ensure same stage workflow works across all three

Who leads:
- Module D + Module B

Success criteria:
- all 3 scenarios can run through the same stage engine
- verifier can trigger rollback suggestions

### Phase 5. Demo hardening
Objective: Prepare for presentation.

Scope:
- polished demo script
- stable sample inputs
- deterministic output style
- fallback plan if retrieval fails
- screenshots or recorded path

Who leads:
- all members, Module A coordinating

Success criteria:
- 3-minute demo runs without improvisation
- each scenario has one prepared sample
- final output is presentation-ready

## 4. Detailed work package per team member

## Team Member 1: Frontend / UX / Demo Interaction

### Work Package A1: Stage UI spec
Deliverables:
- one screen flow per stage
- approval, edit, rollback button placement
- display format for decision log

Files:
- Create: `app/frontend/stage_views/stage1.tsx` or `.py`
- Create: `app/frontend/stage_views/stage2.tsx` or `.py`
- Create: `app/frontend/stage_views/stage3.tsx` or `.py`
- Create: `app/frontend/stage_views/stage4.tsx` or `.py`
- Create: `app/frontend/components/decision_log.tsx` or `.py`

### Work Package A2: Session and stage controls
Deliverables:
- next-stage button
- approve/revise button
- rollback button
- stage status indicator

Files:
- Create: `app/frontend/components/stage_controls.*`
- Create: `app/frontend/components/stage_status.*`

### Work Package A3: Final report rendering
Deliverables:
- planner report view
- engineer report view
- citations view

Files:
- Create: `app/frontend/components/planner_report.*`
- Create: `app/frontend/components/engineer_report.*`
- Create: `app/frontend/components/source_list.*`

### Work Package A4: Demo polish
Deliverables:
- preloaded scenario examples
- easy switcher between 3 scenarios
- presentation mode

Files:
- Modify: `app/frontend/pages/index.*`
- Create: `data/demo_inputs/*.json`

## Team Member 2: Backend / Stage Engine / APIs

### Work Package B1: Core schemas
Deliverables:
- stage request schema
- stage response schema
- decision log schema
- rollback schema

Files:
- Create: `app/backend/core/schemas.py`
- Test: `tests/test_report_schema.py`

### Work Package B2: Stage manager
Deliverables:
- stage transition logic
- approval state management
- rollback logic

Files:
- Create: `app/backend/core/stage_manager.py`
- Create: `app/backend/core/rollback_manager.py`
- Test: `tests/test_stage_manager.py`

### Work Package B3: Orchestrator
Deliverables:
- route request by stage
- call retrieval/planner/verifier/report services
- merge short-term memory into prompts

Files:
- Create: `app/backend/core/orchestrator.py`
- Create: `app/backend/services/memory_service.py`

### Work Package B4: API routes
Deliverables:
- create session
- submit stage input
- approve stage
- rollback stage
- fetch final report

Files:
- Create: `app/backend/main.py`
- Create: `app/backend/api/routes_stage.py`
- Create: `app/backend/api/routes_session.py`
- Create: `app/backend/api/routes_report.py`

## Team Member 3: Retrieval / MCP / Knowledge Base

### Work Package C1: Source inventory and folder structure
Deliverables:
- categorize sources by papers/docs/cases/laws/datasets/patents
- seed the knowledge folder with initial files and README notes

Files:
- Create: `knowledge/papers/README.md`
- Create: `knowledge/docs/README.md`
- Create: `knowledge/cases/README.md`
- Create: `knowledge/laws/README.md`
- Create: `knowledge/datasets/README.md`
- Create: `knowledge/patents/README.md`

### Work Package C2: Retrieval adapter contracts
Deliverables:
- common retrieval interface
- stub implementations for paper/doc/law/case lookups

Files:
- Create: `app/backend/integrations/retrieval_adapter.py`
- Create: `app/backend/integrations/web_search_adapter.py`
- Create: `app/backend/integrations/github_adapter.py`
- Create: `app/backend/integrations/legal_adapter.py`
- Test: `tests/test_retrieval_adapters.py`

### Work Package C3: MCP Hub configuration draft
Deliverables:
- initial mcphub config
- documented required API keys
- recommended MCP set for the project

Files:
- Create: `config/mcphub.example.json`
- Create: `docs/mcp-setup-notes.md`

Recommended MCP first pass:
- Fetch
- GitHub
- File System
- Brave Search or Tavily
- Memory
- optional: Playwright

### Work Package C4: legalize-kr integration
Deliverables:
- local clone strategy or remote GitHub access strategy
- law lookup conventions for Korean regulations
- example queries for logistics/privacy/notifications

Files:
- Create: `knowledge/laws/legalize-kr-notes.md`
- Create: `app/backend/integrations/legal_adapter.py` behavior notes

## Team Member 4: Prompts / Verifier / Evaluation

### Work Package D1: Common stage prompt templates
Deliverables:
- system prompt
- stage 1 prompt
- stage 2 prompt
- stage 3 prompt
- stage 4 prompt

Files:
- Create: `prompts/common/system.md`
- Create: `prompts/common/stage_1.md`
- Create: `prompts/common/stage_2.md`
- Create: `prompts/common/stage_3.md`
- Create: `prompts/common/stage_4.md`

### Work Package D2: Scenario-specific prompt overlays
Deliverables:
- dispatch scenario overlay
- ETA scenario overlay
- failed-delivery scenario overlay

Files:
- Create: `prompts/scenarios/dispatch.md`
- Create: `prompts/scenarios/eta.md`
- Create: `prompts/scenarios/failed_delivery.md`

### Work Package D3: Verifier rules
Deliverables:
- missing-data checks
- over-scoped MVP checks
- KPI-function alignment checks
- regulatory-risk reminder checks
- rollback recommendation logic

Files:
- Create: `app/backend/services/verifier_service.py`
- Test: `tests/test_verifier.py`

### Work Package D4: Evaluation and demo assets
Deliverables:
- golden sample inputs for 3 scenarios
- expected output checklist
- demo evaluation rubric

Files:
- Create: `data/demo_inputs/dispatch.json`
- Create: `data/demo_inputs/eta.json`
- Create: `data/demo_inputs/failed_delivery.json`
- Create: `data/demo_outputs/README.md`
- Create: `docs/demo-rubric.md`

## 5. Integration points the team must agree on early

These are the most dangerous coordination points.

### Integration Point 1: Stage response schema
Every module depends on this.
Minimum fields:
- `stage_id`
- `status`
- `summary`
- `decision_points`
- `required_user_input`
- `citations`
- `rollback_targets`
- `planner_view`
- `engineer_view`

### Integration Point 2: Scenario classification
Need one shared enum:
- `dispatch_recommendation`
- `eta_prediction`
- `failed_delivery_risk`
- `other_last_mile`

### Integration Point 3: Source citation format
Need one shared citation object:
- source type
- title
- url or file path
- short relevance note

### Integration Point 4: Rollback semantics
Need one shared rule:
- soft rollback suggestion
- hard rollback required
- blocked until user resolves

## 6. Suggested 4-person working schedule

### Week 1: specification freeze
Member 1
- UI wireframes
- stage interaction design

Member 2
- schemas and stage manager draft

Member 3
- source inventory + MCP candidate list

Member 4
- prompt structure + verifier rubric draft

Shared checkpoint at end of week:
- agree on schema
- agree on stage outputs
- agree on repository structure

### Week 2: vertical slice for one scenario
Member 1
- implement stage UI for one scenario

Member 2
- implement backend stage flow with mocks

Member 3
- build first retrieval adapters with mock or simple fetch

Member 4
- draft stage prompts and sample outputs for dispatch scenario

Shared checkpoint:
- dynamic dispatch scenario runs end-to-end with mocks

### Week 3: real retrieval + verifier + extra scenarios
Member 1
- improve UI and reports

Member 2
- connect backend to real retrieval adapters

Member 3
- MCP config + legalize-kr + source citations

Member 4
- add ETA and failed-delivery prompts + verifier rules

Shared checkpoint:
- all 3 scenarios supported
- stage 3 verifier active

### Week 4: demo hardening
Member 1
- polish frontend demo mode

Member 2
- stabilize API and rollback behavior

Member 3
- finalize source pack and fallback retrieval plan

Member 4
- finalize scripts, evaluation rubric, expected outputs

Shared checkpoint:
- final dry run
- slide screenshots
- contingency plan if API/MCP fails

## 7. Minimum viable implementation target

If time becomes tight, reduce scope in this order.

Keep:
- stage workflow
- one real scenario fully implemented
- at least one real retrieval path
- verifier logic
- planner/engineer split output

Cut later if needed:
- multi-agent decomposition
- advanced long-term memory
- fancy frontend
- full database persistence
- all three scenarios fully interactive

If very tight:
- fully implement dispatch scenario
- keep ETA and failed-delivery as template-backed semi-static examples

## 8. Definition of done

The prototype is done when all of the following are true:
- user can complete stage 1 to stage 4 for the dispatch scenario
- at least one rollback path works
- planner report and engineer report are both generated
- retrieval cites at least 3 real sources in the final output
- one legal source path is demonstrated
- the same stage framework is shown to apply to ETA and failed-delivery scenarios
- the team can demo the system in under 5 minutes without manual patching

## 9. Final recommendation on implementation strategy

Start narrow.
Do not begin by building a fully general agent platform.
Build one strong vertical slice around dynamic dispatch first, then generalize the same stage engine to ETA and failed-delivery scenarios.

Best first integrated milestone:
- frontend with 4 stages
- backend stage manager
- one retrieval adapter using markdown/fetch/github
- one verifier
- one complete dispatch demo

Once that is stable, the remaining two scenarios should be added mostly through prompt overlays, retrieval variations, and verifier checks rather than rebuilding the architecture.
