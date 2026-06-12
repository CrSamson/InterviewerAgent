# InterviewerAgent

This repository contains an experimental CrewAI notebook for interview preparation:

- [`experimentation_part2.ipynb`](experimentation_part2.ipynb)

The notebook researches a target company and interviewer, generates interview questions for a specific role, and then runs an interactive practice loop where the user answers questions and receives coaching feedback.

The same workflow is now available as a Rich-powered CLI app:

```powershell
.\interview
```

To install the console script, run:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
interviewer-agent run
```

You can also pass the interview context up front:

```powershell
.\interview `
  --company "Maneva" `
  --interviewer "Avery Smith" `
  --position "Forward Deployed Engineer" `
  --job-description "Build AI workflows for industrial customers." `
  --questions 5 `
  --research-depth fast `
  --max-attempts 3
```

The CLI renders a terminal "operator console" with Rich panels, a callback-driven live dashboard, concise Markdown feedback, and phase markers for `BOOT`, `RESEARCH`, `QUESTION GEN`, `PRACTICE`, and `SESSION SAVED`. During research, real CrewAI task callbacks update the company/interviewer/question progress bars, while tool callbacks update the current activity line. By default it uses faster research, generates 5 questions, pauses before practice begins, and writes session history to `runs/interview-session-YYYYMMDD-HHMMSS.json` unless `--output` is provided. Use `--research-depth standard` for the original deeper research mode.

## Architecture Diagrams

Interview-ready PNG diagrams are available in [`diagrams/`](diagrams/):

- [`interviewer-agent-architecture.png`](diagrams/interviewer-agent-architecture.png)
- [`interviewer-agent-agentic-flow.png`](diagrams/interviewer-agent-agentic-flow.png)

Regenerate them with:

```powershell
.\.venv\Scripts\python.exe .\scripts\generate_diagrams.py
```

## High-Level Flow

```text
User inputs
  -> Research company
  -> Research interviewer
  -> Generate interview questions
  -> Parse questions from Markdown
  -> Ask questions one by one
  -> Collect user answer
  -> Generate feedback
  -> Retry answer or move to next question
```

## Required Environment Variables

The notebook expects these values to be available, usually through a `.env` file:

```env
ANTHROPIC_API_KEY=...
SERPER_API_KEY=...
```

`ANTHROPIC_API_KEY` is used by Claude through CrewAI.  
`SERPER_API_KEY` is used by Serper for web search.

## Main Libraries

The notebook uses:

- `crewai`
- `crewai_tools`
- `python-dotenv`
- `IPython.display`
- `re`

The key CrewAI imports are:

```python
from crewai import Agent, Process, Crew, Task
from crewai_tools import ScrapeWebsiteTool, SerperDevTool
```

## LLM Configuration

The workflow uses Anthropic Claude through CrewAI:

```python
llm = LLM(
    model="anthropic/claude-sonnet-4-6",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    temperature=0.2,
    max_tokens=1600,
)
```

`claude-sonnet-4-6` is used because the workflow needs tool calling. Earlier Claude Sonnet 4 model IDs caused strict-tool compatibility errors with CrewAI.

`temperature` is kept low (`0.2`) on purpose: question generation must produce a stable, parseable format, so reproducibility is preferred over creative variety. The CLI configuration lives in [`interviewer_agent/workflow.py`](interviewer_agent/workflow.py).

## User Inputs

The notebook asks for:

- interviewer name
- company name
- job position
- job description

These values are stored in:

```python
interviewer
company
job_position
job_description
```

They are then interpolated into the research tasks and question-generation prompt.

## Research Tools

The research agent uses two tools:

```python
search_tool = SerperDevTool(n_results=5, max_usage_count=3)
scrape_tool = ScrapeWebsiteTool(max_usage_count=4)
```

Tool limits are intentional:

- Serper can search the web at most 3 times.
- The scraper can read at most 4 webpages.
- Serper returns 5 results per search.

This prevents the research agent from repeatedly searching and spending unnecessary tokens.

## Agents

### Research Agent

The `research_agent` gathers company and interviewer context.

```python
research_agent = Agent(
    role="Researcher Agent",
    goal="Conduct in depth research on a company.",
    backstory="As a Research specialist your mission is to conduct in depth research on a company.",
    llm=llm,
    tools=[scrape_tool, search_tool],
    max_iter=8,
)
```

Important details:

- It can search and scrape the web.
- It has a limited number of tool calls.
- `max_iter=8` limits its reasoning/tool-use loop.

### AI Interview Coach

The `coach_agent` generates questions and later grades answers.

```python
coach_agent = Agent(
    role="AI Interview Coach",
    goal=f"Coach the user to prepare for an interview for the {job_position} role at {company} by grading the user's answer.",
    backstory=f"You are an expert on technical job interviews in companies like {company}.",
    llm=llm,
)
```

## Main Tasks

### 1. Company Research

`research_company_task` asks the research agent to gather company information relevant to the target role.

### 2. Interviewer Research

`research_person_task` asks the research agent to gather public information about the interviewer.

### 3. Question Generation

`define_questions_task` asks the coach agent to generate the requested number of
interview questions (default 5, configurable with `--questions`) using:

- job description
- company research
- interviewer research

It uses the two research tasks as context:

```python
context=[research_company_task, research_person_task]
```

To keep the output deterministic and reliably parseable, the task prompt pins an
exact output format instead of asking for free-form Markdown:

- exactly N lines, one question per line;
- each line numbered `1.`, `2.`, `3.`, and so on;
- no title, preamble, closing remark, blank lines, bullets, bold/italic markup, or
  surrounding quotes.

This canonical numbered shape maps directly onto the parser's numbered pattern, so a
well-behaved model run parses cleanly every time.

## Main Crew

The main crew runs the three tasks sequentially:

```python
crew = Crew(
    agents=[research_agent, coach_agent],
    tasks=[research_company_task, research_person_task, define_questions_task],
    verbose=True,
    process=Process.sequential,
    embedder=embedder,
)

result = await crew.kickoff_async({
    "topic": "Write a list of question to prepare for the interview."
})
```

Task order:

1. Research the company.
2. Research the interviewer.
3. Generate interview questions.

The notebook uses `await crew.kickoff_async(...)` because Jupyter already runs an event loop. Calling `crew.kickoff(...)` synchronously inside a notebook can fail.

## Question Extraction

The generated questions are stored as raw Markdown:

```python
questions = result.tasks_output[2].raw
```

Important: `questions` is a Markdown string, not a Python list.

The CLI parses it with `parse_interview_questions` in
[`interviewer_agent/parsing.py`](interviewer_agent/parsing.py). Even though the prompt
asks for a canonical numbered list, models occasionally drift, so the parser is
tolerant and recognizes several shapes:

- numbered lines (`1.`, `2)`, `3:`) — the canonical, deterministic format;
- plain Markdown bullets (`-`, `*`, `+`);
- notebook-style `**Question N:**` blocks with quoted text;
- same-line `**Question N:** ...` entries.

It also trims wrapping markup/quotes and de-duplicates repeated questions. Earlier the
parser only handled the `**Question N:**` notebook format; when a model returned plain
bullets, nothing matched and question generation failed with
`The model returned question text, but no questions could be parsed`. The deterministic
prompt plus the tolerant parser together prevent that failure mode.

## Deprecated Experiment: `human_input=True`

The notebook contains an older experiment using:

```python
human_input=True
```

This is not the recommended approach for interview practice.

In CrewAI, `human_input=True` means the human reviews the agent's final output. It does not behave like a clean interview-answer input mechanism. In this project, it caused the agent to receive the user's answer as feedback on its own generated question, which could make it repeat the question.

Use Python `input()` instead.

## Basic Practice Loop

The notebook includes a simple loop that:

1. Parses questions.
2. Displays one question.
3. Collects the user's answer with `input()`.
4. Sends the question and answer to the coach agent.
5. Displays feedback.
6. Moves to the next question.

This is useful for one attempt per question.

## Iterative Feedback Loop

The final workflow is the iterative practice loop:

```python
practice_history = await practice_interview_with_iterations(
    questions,
    max_attempts_per_question=3,
)
```

For each question, it:

1. Displays the question.
2. Collects an answer attempt.
3. Runs a feedback task with the coach agent.
4. Displays feedback.
5. Lets the user retry the same question.
6. Moves to the next question when the user types `next`.
7. Stops cleanly when the user types `exit`, `quit`, or `stop`.

Each attempt is stored in `practice_history` with:

- question index
- question text
- attempt number
- user answer
- feedback

## Recommended Run Order

1. Load environment variables.
2. Import libraries.
3. Create the LLM.
4. Enter interviewer, company, role, and job description.
5. Create research tools.
6. Create the research agent.
7. Define company and interviewer research tasks.
8. Create the coach agent.
9. Define the question-generation task.
10. Run the main crew.
11. Extract `questions`.
12. Skip the `human_input=True` experiment.
13. Run the iterative feedback loop.

## Current Limitations

- Generated questions are still parsed from Markdown with regex (now tolerant of
  multiple formats), rather than a structured JSON contract.
- The notebook still contains the older `human_input=True` experiment.
- Research output and feedback are mostly raw Markdown.
- There is no structured scoring rubric yet.
- There is no final performance summary across all attempts.

## Suggested Improvements

- Make `define_questions_task` return structured JSON instead of Markdown.
- Remove the deprecated `human_input=True` cells.
- Add a consistent rubric for feedback, such as clarity, depth, relevance, and confidence.
- Save `practice_history` to a file after the session.
- Add a final summary task that reviews all attempts and gives an overall improvement plan.
