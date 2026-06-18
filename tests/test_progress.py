from io import StringIO
import threading
import unittest

from rich.console import Console

from interviewer_agent.progress import Phase, ProgressState
from interviewer_agent.ui import render_dashboard, render_research_body
from interviewer_agent.workflow import _make_progress_callbacks


class FakeAgentAction:
    def __init__(self, tool: str, thought: str = "thinking") -> None:
        self.tool = tool
        self.thought = thought


class FakeAgentFinish:
    def __init__(self, thought: str = "done") -> None:
        self.thought = thought


class FakeTaskOutput:
    def __init__(self, name: str | None = None) -> None:
        self.name = name


class ProgressStateTests(unittest.TestCase):
    def test_task_callbacks_complete_three_research_tasks(self) -> None:
        state = ProgressState(depth="fast", question_count=5, max_attempts=3)
        task_callback, _ = _make_progress_callbacks(
            state,
            FakeAgentAction,
            FakeAgentFinish,
        )

        task_callback(FakeTaskOutput("company"))
        task_callback(FakeTaskOutput("interviewer"))
        task_callback(FakeTaskOutput("questions"))

        snapshot = state.snapshot()
        self.assertEqual(snapshot.research_completed, 3)
        self.assertTrue(all(task.done for task in snapshot.research_tasks))

    def test_task_callback_uses_sequential_fallback_when_name_missing(self) -> None:
        state = ProgressState(depth="fast", question_count=5, max_attempts=3)
        task_callback, _ = _make_progress_callbacks(
            state,
            FakeAgentAction,
            FakeAgentFinish,
        )

        task_callback(FakeTaskOutput())
        task_callback(FakeTaskOutput())

        snapshot = state.snapshot()
        done = [task.key for task in snapshot.research_tasks if task.done]
        self.assertEqual(done, ["company", "interviewer"])

    def test_task_callback_fallback_skips_named_completed_tasks(self) -> None:
        state = ProgressState(depth="fast", question_count=5, max_attempts=3)
        task_callback, _ = _make_progress_callbacks(
            state,
            FakeAgentAction,
            FakeAgentFinish,
        )

        task_callback(FakeTaskOutput("company"))
        task_callback(FakeTaskOutput())

        done = [task.key for task in state.snapshot().research_tasks if task.done]
        self.assertEqual(done, ["company", "interviewer"])

    def test_step_callback_surfaces_thoughts_without_counting_tools(self) -> None:
        # Tool calls are counted by the event-bus listener, not step_callback,
        # so AgentAction steps must not increment the counter (the ReAct path
        # would otherwise double-count).
        state = ProgressState(depth="fast", question_count=5, max_attempts=3)
        _, step_callback = _make_progress_callbacks(
            state,
            FakeAgentAction,
            FakeAgentFinish,
        )

        step_callback(FakeAgentAction("serper_search", thought="searching the web"))
        self.assertEqual(state.snapshot().now_line, "searching the web")

        step_callback(FakeAgentFinish("final answer ready"))

        snapshot = state.snapshot()
        self.assertEqual(snapshot.tool_calls, 0)
        self.assertEqual(snapshot.now_line, "final answer ready")

    def test_tool_call_counter_is_thread_safe(self) -> None:
        state = ProgressState(depth="fast", question_count=5, max_attempts=3)

        def hammer() -> None:
            for _ in range(1000):
                state.note_tool_call("search")

        threads = [threading.Thread(target=hammer), threading.Thread(target=hammer)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(state.snapshot().tool_calls, 2000)

    def test_research_body_renders_to_console_text(self) -> None:
        state = ProgressState(depth="fast", question_count=5, max_attempts=3)
        state.set_phase(Phase.RESEARCH)
        state.note_tool_call("SerperDevTool")
        state.complete_task("company")
        snapshot = state.snapshot()
        output = StringIO()
        console = Console(file=output, force_terminal=False, width=100)

        console.print(render_research_body(snapshot))

        rendered = output.getvalue()
        self.assertIn("LIVE RESEARCH DASHBOARD", rendered)
        self.assertIn("Company brief", rendered)
        self.assertIn("Tool calls", rendered)

    def test_dashboard_renders_stepper_body_and_footer(self) -> None:
        state = ProgressState(depth="fast", question_count=5, max_attempts=3)
        state.set_phase(Phase.RESEARCH)
        output = StringIO()
        console = Console(file=output, force_terminal=False, width=120)

        console.print(render_dashboard(state.snapshot()))

        rendered = output.getvalue()
        self.assertIn("[>] RESEARCH", rendered)
        self.assertIn("LIVE RESEARCH DASHBOARD", rendered)
        self.assertIn("mode=fast", rendered)


if __name__ == "__main__":
    unittest.main()
