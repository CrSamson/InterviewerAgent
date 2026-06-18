from __future__ import annotations

import os
from collections.abc import Mapping
import threading
from typing import Any

from dotenv import load_dotenv

from .models import (
    FeedbackReport,
    InterviewInputs,
    QuestionDeck,
    QuestionGenerationResult,
    ResearchBrief,
    SessionRecord,
    SessionSummary,
    WorkflowSettings,
)
from .parsing import parse_feedback_report, parse_interview_questions, parse_session_summary
from .progress import ProgressState


REQUIRED_ENV_VARS = ("ANTHROPIC_API_KEY", "SERPER_API_KEY")
MODEL_NAME = "anthropic/claude-sonnet-4-6"


class MissingEnvironmentError(RuntimeError):
    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        names = ", ".join(missing)
        super().__init__(f"Missing required environment variables: {names}")


def validate_environment(env: Mapping[str, str | None] | None = None) -> dict[str, str]:
    source = os.environ if env is None else env
    missing = [key for key in REQUIRED_ENV_VARS if not source.get(key)]
    if missing:
        raise MissingEnvironmentError(missing)
    return {key: str(source[key]) for key in REQUIRED_ENV_VARS}


def load_environment() -> dict[str, str]:
    load_dotenv()
    return validate_environment()


class CrewAIInterviewEngine:
    def __init__(
        self,
        inputs: InterviewInputs,
        *,
        verbose: bool = False,
        settings: WorkflowSettings | None = None,
    ) -> None:
        self.inputs = inputs
        self.verbose = verbose
        self.settings = settings or WorkflowSettings()
        self._llm = None
        self._coach_agent = None
        self._tool_listener_registered = False

    async def generate_research_brief(
        self,
        progress: ProgressState | None = None,
    ) -> ResearchBrief:
        load_environment()
        (
            Agent,
            Crew,
            LLM,
            Process,
            Task,
            ScrapeWebsiteTool,
            SerperDevTool,
            AgentAction,
            AgentFinish,
        ) = _load_crewai()

        research_limits = _research_limits(self.settings.research_depth)
        llm = self._get_llm(LLM)
        search_tool = SerperDevTool(
            n_results=research_limits["search_results"],
            max_usage_count=research_limits["search_calls"],
        )
        scrape_tool = ScrapeWebsiteTool(max_usage_count=research_limits["scrape_calls"])

        research_agent = Agent(
            role="Researcher Agent",
            goal="Conduct focused interview-preparation research.",
            backstory=(
                "As a research specialist, find only the company and interviewer "
                "context that will materially improve interview preparation."
            ),
            llm=llm,
            tools=[scrape_tool, search_tool],
            max_iter=research_limits["max_iter"],
        )

        research_company_task = Task(
            name="company",
            description=(
                f"Conduct research on the company {self.inputs.company} and find "
                "relevant information that can help with the interview preparation "
                f"for the position of {self.inputs.job_position}. Keep this concise: "
                "focus on business model, AI/engineering relevance, culture signals, "
                "and interview-useful talking points only."
            ),
            expected_output="A concise Markdown brief with no more than 8 bullet points.",
            agent=research_agent,
        )

        research_person_task = Task(
            name="interviewer",
            description=(
                f"Conduct research on the interviewer {self.inputs.interviewer} and "
                "find relevant information that can help with the interview "
                f"preparation for the position of {self.inputs.job_position}. Keep "
                "this concise and use only public, interview-relevant information."
            ),
            expected_output="A concise Markdown brief with no more than 6 bullet points.",
            agent=research_agent,
        )

        task_callback = None
        step_callback = None
        if progress:
            task_callback, step_callback = _make_progress_callbacks(
                progress,
                AgentAction,
                AgentFinish,
            )
            if not self._tool_listener_registered:
                _register_tool_usage_listener(progress)
                self._tool_listener_registered = True

        crew = Crew(
            agents=[research_agent],
            tasks=[research_company_task, research_person_task],
            verbose=self.verbose,
            process=Process.sequential,
            embedder={"provider": "onnx", "config": {}},
            task_callback=task_callback,
            step_callback=step_callback,
        )

        result = await crew.kickoff_async(
            {"topic": "Research interview context."}
        )
        outputs = list(getattr(result, "tasks_output", []) or [])
        return ResearchBrief(
            company_research=_task_output_raw(outputs, 0),
            interviewer_research=_task_output_raw(outputs, 1),
        )

    async def generate_question_deck(
        self,
        *,
        research: ResearchBrief,
        progress: ProgressState | None = None,
    ) -> QuestionDeck:
        load_environment()
        Agent, Crew, LLM, Process, Task, *_ = _load_crewai()
        coach_agent = self._get_coach_agent(Agent, self._get_llm(LLM))

        define_questions_task = Task(
            name="questions",
            description=(
                f"Company research brief:\n{research.company_research}\n\n"
                f"Interviewer research brief:\n{research.interviewer_research}\n\n"
                f"Based on the job description: {self.inputs.job_description}, "
                f"prepare exactly {self.settings.question_count} relevant interview "
                f"questions for the position of {self.inputs.job_position} at "
                f"{self.inputs.company}. Prefer practical, high-signal questions over "
                "broad generic questions.\n\n"
                "Output format (follow exactly):\n"
                f"- Output exactly {self.settings.question_count} lines, one question "
                "per line.\n"
                "- Number each line as `1.`, `2.`, `3.`, and so on.\n"
                "- Put the full question text right after the number on the same line.\n"
                "- Write nothing else: no title, no preamble, no closing remark, no "
                "blank lines, no bullets, no bold or italic markup, no surrounding "
                "quotes.\n\n"
                "Example shape:\n"
                "1. First question here?\n"
                "2. Second question here?"
            ),
            expected_output=(
                f"Exactly {self.settings.question_count} lines, each starting with "
                "`<n>.` followed by one interview question, and nothing else."
            ),
            agent=coach_agent,
        )

        task_callback = None
        step_callback = None
        if progress:
            task_callback, step_callback = _make_single_task_progress_callbacks(
                progress,
                "questions",
            )

        crew = Crew(
            agents=[coach_agent],
            tasks=[define_questions_task],
            verbose=self.verbose,
            process=Process.sequential,
            task_callback=task_callback,
            step_callback=step_callback,
        )

        result = await crew.kickoff_async(
            {"topic": "Write a list of questions to prepare for the interview."}
        )
        outputs = list(getattr(result, "tasks_output", []) or [])
        questions_markdown = _task_output_raw(outputs, 0) or str(result)
        questions = parse_interview_questions(questions_markdown)[: self.settings.question_count]

        return QuestionDeck(
            questions_markdown=questions_markdown,
            questions=questions,
        )

    async def generate_questions(
        self,
        progress: ProgressState | None = None,
    ) -> QuestionGenerationResult:
        research = await self.generate_research_brief(progress=progress)
        deck = await self.generate_question_deck(research=research, progress=progress)
        return QuestionGenerationResult(
            company_research=research.company_research,
            interviewer_research=research.interviewer_research,
            questions_markdown=deck.questions_markdown,
            questions=deck.questions,
        )

    async def generate_answer_feedback(
        self,
        *,
        question: str,
        answer: str,
        attempt_number: int,
    ) -> FeedbackReport:
        load_environment()
        Agent, Crew, LLM, Process, Task, *_ = _load_crewai()
        coach_agent = self._get_coach_agent(Agent, self._get_llm(LLM))

        feedback_task = Task(
            description=f"""
You are coaching a candidate for a technical interview.

Interview question:
{question}

Candidate answer attempt #{attempt_number}:
{answer}

Give feedback that helps the candidate improve the next attempt.

Output exactly these five fields, one per paragraph:
Score: <integer from 1 to 5>/5
What worked: <one concise sentence>
Missing signal: <one concise sentence>
Stronger outline: <one concise sentence>
Next revision: <one concrete instruction>

Keep the full response under 180 words. Do not use tables or emoji.
""",
            expected_output="Structured coaching feedback with score and four rubric fields.",
            agent=coach_agent,
        )

        feedback_crew = Crew(
            agents=[coach_agent],
            tasks=[feedback_task],
            verbose=self.verbose,
            process=Process.sequential,
        )

        return parse_feedback_report(str(await feedback_crew.kickoff_async()))

    async def generate_session_summary(
        self,
        *,
        session: SessionRecord,
    ) -> SessionSummary:
        if not session.attempts:
            return SessionSummary(
                recurring_gaps="No completed answers were recorded.",
                strongest_answer="No answer attempts to compare.",
                weakest_answer="No answer attempts to compare.",
                next_practice_plan="Run another session and answer at least one question.",
            )

        load_environment()
        Agent, Crew, LLM, Process, Task, *_ = _load_crewai()
        coach_agent = self._get_coach_agent(Agent, self._get_llm(LLM))
        attempts = "\n\n".join(
            [
                (
                    f"Q{attempt.question_index}, attempt {attempt.attempt}\n"
                    f"Question: {_truncate(attempt.question, 280)}\n"
                    f"Answer: {_truncate(attempt.answer, 700)}\n"
                    f"Feedback: {_truncate(attempt.feedback, 500)}"
                )
                for attempt in session.attempts
            ]
        )
        summary_task = Task(
            description=f"""
You are summarizing an interview practice session for a candidate.

Role: {session.inputs.job_position}
Company: {session.inputs.company}

Attempts:
{attempts}

Output exactly these four fields, one per paragraph:
Recurring gaps: <patterns the candidate should improve>
Strongest answer: <question or answer that was strongest and why>
Weakest answer: <question or answer that needs the most work and why>
Next practice plan: <specific next steps for the next session>

Keep the full response under 220 words. Do not use tables or emoji.
""",
            expected_output="Structured session summary with four fields.",
            agent=coach_agent,
        )
        summary_crew = Crew(
            agents=[coach_agent],
            tasks=[summary_task],
            verbose=self.verbose,
            process=Process.sequential,
        )

        return parse_session_summary(str(await summary_crew.kickoff_async()))

    def _get_llm(self, LLM):
        if self._llm is None:
            self._llm = LLM(
                model=MODEL_NAME,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                temperature=0.2,
                max_tokens=1600,
            )
        return self._llm

    def _get_coach_agent(self, Agent, llm):
        if self._coach_agent is None:
            self._coach_agent = Agent(
                role="AI Interview Coach",
                goal=(
                    "Coach the user to prepare for an interview for the "
                    f"{self.inputs.job_position} role at {self.inputs.company} by "
                    "grading the user's answer."
                ),
                backstory=(
                    "You are an expert on technical job interviews in companies like "
                    f"{self.inputs.company}."
                ),
                llm=llm,
            )
        return self._coach_agent


CrewInterviewWorkflow = CrewAIInterviewEngine


def _load_crewai():
    from crewai import Agent, Crew, LLM, Process, Task
    from crewai.agents.parser import AgentAction, AgentFinish
    from crewai_tools import ScrapeWebsiteTool, SerperDevTool

    return (
        Agent,
        Crew,
        LLM,
        Process,
        Task,
        ScrapeWebsiteTool,
        SerperDevTool,
        AgentAction,
        AgentFinish,
    )


def _make_progress_callbacks(
    progress: ProgressState,
    AgentAction: type[Any],
    AgentFinish: type[Any],
):
    task_order = ("company", "interviewer", "questions")
    ordinal_index = 0
    ordinal_lock = threading.Lock()
    completed: set[str] = set()

    def task_callback(output: Any) -> None:
        nonlocal ordinal_index
        name = getattr(output, "name", None)
        key = str(name).strip().casefold() if name else ""
        if key not in task_order:
            with ordinal_lock:
                while (
                    ordinal_index < len(task_order)
                    and task_order[ordinal_index] in completed
                ):
                    ordinal_index += 1
                key = task_order[min(ordinal_index, len(task_order) - 1)]
                ordinal_index += 1
        completed.add(key)
        progress.complete_task(key)

    def step_callback(step: Any) -> None:
        # Tool calls are counted via the event bus (see
        # _register_tool_usage_listener); with native function calling the
        # executor never passes AgentAction tool steps to this callback, and
        # counting here too would double-count on the ReAct path.
        if isinstance(step, (AgentAction, AgentFinish)):
            thought = getattr(step, "thought", "") or getattr(step, "text", "")
            progress.note_thinking(str(thought))
            return
        thought = getattr(step, "thought", None)
        if thought:
            progress.note_thinking(str(thought))

    return task_callback, step_callback


def _make_single_task_progress_callbacks(progress: ProgressState, key: str):
    def task_callback(output: Any) -> None:
        progress.complete_task(key)

    def step_callback(step: Any) -> None:
        thought = getattr(step, "thought", "") or getattr(step, "text", "")
        if thought:
            progress.note_thinking(str(thought))

    return task_callback, step_callback


def _register_tool_usage_listener(progress: ProgressState) -> None:
    """Count tool calls via CrewAI's event bus.

    Claude uses native function calling, where Crew.step_callback only fires
    with AgentFinish payloads -- tool executions never surface as AgentAction
    steps. ToolUsageStartedEvent fires on every tool execution regardless of
    the calling path. The handler stays registered for the process lifetime,
    which is fine for a single CLI session.
    """
    from crewai.events import ToolUsageStartedEvent, crewai_event_bus

    @crewai_event_bus.on(ToolUsageStartedEvent)
    def _on_tool_usage_started(source: Any, event: Any) -> None:
        progress.note_tool_call(str(getattr(event, "tool_name", "") or "tool"))


def _research_limits(depth: str) -> dict[str, int]:
    if depth == "standard":
        return {
            "search_results": 5,
            "search_calls": 3,
            "scrape_calls": 4,
            "max_iter": 8,
        }
    return {
        "search_results": 3,
        "search_calls": 2,
        "scrape_calls": 1,
        "max_iter": 4,
    }


def _task_output_raw(outputs: list[object], index: int) -> str:
    if index >= len(outputs):
        return ""
    output = outputs[index]
    return str(getattr(output, "raw", output) or "")


def _truncate(value: str, limit: int) -> str:
    compact = " ".join(str(value).split())
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 3)].rstrip() + "..."
