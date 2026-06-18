# Graph Report - .  (2026-06-15)

## Corpus Check
- Corpus is ~19,681 words - fits in a single context window. You may not need a graph.

## Summary
- 283 nodes · 1179 edges · 15 communities (14 shown, 1 thin omitted)
- Extraction: 62% EXTRACTED · 38% INFERRED · 0% AMBIGUOUS · INFERRED: 452 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Controller UI Flow|Controller UI Flow]]
- [[_COMMUNITY_CLI Crew Workflow|CLI Crew Workflow]]
- [[_COMMUNITY_Progress Tracking|Progress Tracking]]
- [[_COMMUNITY_Diagram Generation|Diagram Generation]]
- [[_COMMUNITY_Parsing Logic|Parsing Logic]]
- [[_COMMUNITY_Controller Tests|Controller Tests]]
- [[_COMMUNITY_Deck Preparation|Deck Preparation]]
- [[_COMMUNITY_Practice Loop Tests|Practice Loop Tests]]
- [[_COMMUNITY_Workflow Data Models|Workflow Data Models]]
- [[_COMMUNITY_Session Summary|Session Summary]]
- [[_COMMUNITY_Session Recording|Session Recording]]
- [[_COMMUNITY_Engine Research Deck|Engine Research Deck]]
- [[_COMMUNITY_Summary Coercion|Summary Coercion]]
- [[_COMMUNITY_Session Events|Session Events]]
- [[_COMMUNITY_Answer Feedback|Answer Feedback]]

## God Nodes (most connected - your core abstractions)
1. `SessionSummary` - 68 edges
2. `FeedbackReport` - 67 edges
3. `InterviewInputs` - 64 edges
4. `WorkflowSettings` - 57 edges
5. `SessionRecord` - 56 edges
6. `ProgressState` - 56 edges
7. `QuestionDeck` - 48 edges
8. `ResearchBrief` - 46 edges
9. `CrewAIInterviewEngine` - 39 edges
10. `Phase` - 35 edges

## Surprising Connections (you probably didn't know these)
- `_FakeConsole` --uses--> `InterviewInputs`  [INFERRED]
  tests/test_cli_practice.py → interviewer_agent/models.py
- `_FakeStatus` --uses--> `InterviewInputs`  [INFERRED]
  tests/test_cli_practice.py → interviewer_agent/models.py
- `_FakeWorkflow` --uses--> `InterviewInputs`  [INFERRED]
  tests/test_cli_practice.py → interviewer_agent/models.py
- `PracticeLoopTests` --uses--> `InterviewInputs`  [INFERRED]
  tests/test_cli_practice.py → interviewer_agent/models.py
- `SessionRecordTests` --uses--> `InterviewInputs`  [INFERRED]
  tests/test_models.py → interviewer_agent/models.py

## Import Cycles
- None detected.

## Communities (15 total, 1 thin omitted)

### Community 0 - "Controller UI Flow"
Cohesion: 0.12
Nodes (51): Group, _build_example_answer(), _build_hint(), _collect_inputs(), _default_output_path(), _edit_context_value(), _edit_question(), _practice_loop() (+43 more)

### Community 1 - "CLI Crew Workflow"
Cohesion: 0.10
Nodes (24): Context, help, callback(), Path, Launch the guided interview preparation session., run(), _run_async(), Command-line interview preparation workflow. (+16 more)

### Community 2 - "Progress Tracking"
Cohesion: 0.14
Nodes (12): Enum, _clean_tool_name(), Phase, _phase_now_line(), ProgressState, TaskProgress, _make_progress_callbacks(), str (+4 more)

### Community 3 - "Diagram Generation"
Cohesion: 0.28
Nodes (22): FreeTypeFont, Image, ImageDraw, agentic_flow_diagram(), architecture_diagram(), arrow(), canvas(), chip() (+14 more)

### Community 4 - "Parsing Logic"
Cohesion: 0.18
Nodes (12): _coerce_feedback_report(), clean_question(), parse_feedback_report(), parse_interview_questions(), _parse_line_oriented_questions(), _parse_named_fields(), _parse_score(), parse_session_summary() (+4 more)

### Community 5 - "Controller Tests"
Cohesion: 0.17
Nodes (8): parse_practice_command(), PracticeCommand, FakeEngine, PracticeCommandTests, QuestionDeck, ResearchBrief, RunSessionControllerTests, ScriptedConsole

### Community 6 - "Deck Preparation"
Cohesion: 0.29
Nodes (15): InterviewEngine, _prepare_deck(), _prepare_deck_with_live_progress(), FeedbackReport, Path, ProgressState, QuestionDeck, ResearchBrief (+7 more)

### Community 7 - "Practice Loop Tests"
Cohesion: 0.20
Nodes (4): _FakeConsole, _FakeStatus, _FakeWorkflow, PracticeLoopTests

### Community 8 - "Workflow Data Models"
Cohesion: 0.33
Nodes (12): InterviewInputs, QuestionGenerationResult, ResearchBrief, Any, FeedbackReport, InterviewInputs, QuestionDeck, ResearchBrief (+4 more)

### Community 9 - "Session Summary"
Cohesion: 0.24
Nodes (10): SessionRecord, SessionSummary, Summarize the completed practice session., FeedbackReport, WorkflowSettings, Any, FeedbackReport, InterviewInputs (+2 more)

### Community 10 - "Session Recording"
Cohesion: 0.26
Nodes (4): PracticeAttempt, SessionRecord, utc_now_iso(), SessionRecordTests

### Community 11 - "Engine Research Deck"
Cohesion: 0.33
Nodes (5): ProgressState, QuestionDeck, ResearchBrief, Research company and interviewer context for the session., Generate an interview question deck from reviewed context.

### Community 12 - "Summary Coercion"
Cohesion: 0.60
Nodes (6): _coerce_session_summary(), Any, SessionRecord, SessionSummary, _summarize_session(), SessionSummary

### Community 13 - "Session Events"
Cohesion: 0.33
Nodes (3): Any, Path, SessionEvent

## Knowledge Gaps
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ProgressState` connect `Progress Tracking` to `Controller UI Flow`, `CLI Crew Workflow`, `Controller Tests`, `Deck Preparation`, `Workflow Data Models`, `Session Summary`, `Session Recording`, `Engine Research Deck`, `Summary Coercion`, `Answer Feedback`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Why does `SessionRecord` connect `Session Recording` to `Controller UI Flow`, `CLI Crew Workflow`, `Controller Tests`, `Deck Preparation`, `Practice Loop Tests`, `Workflow Data Models`, `Session Summary`, `Engine Research Deck`, `Summary Coercion`, `Session Events`, `Answer Feedback`?**
  _High betweenness centrality (0.087) - this node is a cross-community bridge._
- **Why does `InterviewInputs` connect `Workflow Data Models` to `Controller UI Flow`, `CLI Crew Workflow`, `Controller Tests`, `Deck Preparation`, `Practice Loop Tests`, `Session Summary`, `Session Recording`, `Engine Research Deck`, `Summary Coercion`, `Answer Feedback`?**
  _High betweenness centrality (0.079) - this node is a cross-community bridge._
- **Are the 52 inferred relationships involving `SessionSummary` (e.g. with `Group` and `InterviewEngine`) actually correct?**
  _`SessionSummary` has 52 INFERRED edges - model-reasoned connections that need verification._
- **Are the 52 inferred relationships involving `FeedbackReport` (e.g. with `Group` and `InterviewEngine`) actually correct?**
  _`FeedbackReport` has 52 INFERRED edges - model-reasoned connections that need verification._
- **Are the 48 inferred relationships involving `InterviewInputs` (e.g. with `Group` and `InterviewEngine`) actually correct?**
  _`InterviewInputs` has 48 INFERRED edges - model-reasoned connections that need verification._
- **Are the 44 inferred relationships involving `WorkflowSettings` (e.g. with `Group` and `InterviewEngine`) actually correct?**
  _`WorkflowSettings` has 44 INFERRED edges - model-reasoned connections that need verification._