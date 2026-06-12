import unittest

from interviewer_agent.parsing import parse_interview_questions


class ParseInterviewQuestionsTests(unittest.TestCase):
    def test_parse_notebook_markdown_questions(self) -> None:
        questions = """
**Question 1: Technical Depth:**
    *"How would you integrate with an undocumented legacy system?"*

**Question 2: Customer Judgement:**
    *"Tell me about a time you balanced speed and reliability."*
"""

        self.assertEqual(
            parse_interview_questions(questions),
            [
                "How would you integrate with an undocumented legacy system?",
                "Tell me about a time you balanced speed and reliability.",
            ],
        )


    def test_parse_numbered_fallback_questions(self) -> None:
        questions = """
1. How do you debug a production integration failure?
2) Describe a project where you owned the full lifecycle.
3: What tradeoffs would you make for a fast pilot?
"""

        self.assertEqual(
            parse_interview_questions(questions),
            [
                "How do you debug a production integration failure?",
                "Describe a project where you owned the full lifecycle.",
                "What tradeoffs would you make for a fast pilot?",
            ],
        )


    def test_parse_plain_bullet_questions(self) -> None:
        questions = """Here are 5 interview questions:

- How would you architect an agentic system to orchestrate complex processes?
* Describe a time you coached a team on adopting AI-driven development.
+ How do you ensure reliability in a highly regulated environment?
"""

        self.assertEqual(
            parse_interview_questions(questions),
            [
                "How would you architect an agentic system to orchestrate complex processes?",
                "Describe a time you coached a team on adopting AI-driven development.",
                "How do you ensure reliability in a highly regulated environment?",
            ],
        )


    def test_parse_same_line_markdown_questions_and_dedupes(self) -> None:
        questions = """
- **Question 1:** "How do you scope an ambiguous customer problem?"
- **Question 2:** **How do you scope an ambiguous customer problem?**
- **Question 3:** _How do you earn trust with operators?_
"""

        self.assertEqual(
            parse_interview_questions(questions),
            [
                "How do you scope an ambiguous customer problem?",
                "How do you earn trust with operators?",
            ],
        )


if __name__ == "__main__":
    unittest.main()
