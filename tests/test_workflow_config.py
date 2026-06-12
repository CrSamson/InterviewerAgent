import unittest

from interviewer_agent.models import WorkflowSettings
from interviewer_agent.workflow import MissingEnvironmentError, _research_limits, validate_environment


class WorkflowConfigTests(unittest.TestCase):
    def test_validate_environment_reports_all_missing_keys(self) -> None:
        with self.assertRaises(MissingEnvironmentError) as exc_info:
            validate_environment({})

        self.assertEqual(exc_info.exception.missing, ["ANTHROPIC_API_KEY", "SERPER_API_KEY"])


    def test_validate_environment_returns_required_values(self) -> None:
        env = {
            "ANTHROPIC_API_KEY": "anthropic-test",
            "SERPER_API_KEY": "serper-test",
            "IGNORED": "value",
        }

        self.assertEqual(
            validate_environment(env),
            {
                "ANTHROPIC_API_KEY": "anthropic-test",
                "SERPER_API_KEY": "serper-test",
            },
        )

    def test_workflow_settings_defaults_to_fast_five_question_mode(self) -> None:
        settings = WorkflowSettings()

        self.assertEqual(settings.question_count, 5)
        self.assertEqual(settings.research_depth, "fast")

    def test_workflow_settings_rejects_invalid_research_depth(self) -> None:
        with self.assertRaises(ValueError):
            WorkflowSettings(research_depth="deep")

    def test_research_limits_are_lower_in_fast_mode(self) -> None:
        fast = _research_limits("fast")
        standard = _research_limits("standard")

        self.assertLess(fast["search_results"], standard["search_results"])
        self.assertLess(fast["search_calls"], standard["search_calls"])
        self.assertLess(fast["scrape_calls"], standard["scrape_calls"])
        self.assertLess(fast["max_iter"], standard["max_iter"])


if __name__ == "__main__":
    unittest.main()
