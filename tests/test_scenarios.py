import sys

from magi.agents.balthasar import Balthasar
from magi.agents.casper import Casper
from magi.agents.melchior import Melchior
from magi.voting.comparator import compare_agent_results
from magi.voting.report_formatter import format_final_decision_report


class Tee:
    def __init__(self, *files):
        self.files = files

    def write(self, data):
        for f in self.files:
            f.write(data)
            f.flush()

    def flush(self):
        for f in self.files:
            f.flush()


SCENARIOS = [
    {
        "name": "profit_vs_layoffs",
        "description": """
A company can automate a large part of its operations.

Option A: Automate aggressively, increasing profit by 40% but laying off 30% of employees.
Option B: Gradual automation, increasing profit by 15% with minimal layoffs.
Option C: No automation, preserving all jobs but with stagnant profits.
""",
    },
    {
        "name": "privacy_vs_security",
        "description": """
A tech company must decide how to handle user data.

Option A: Collect extensive user data to improve security and personalization.
Option B: Collect minimal data, preserving privacy but limiting system capabilities.
Option C: Balanced data collection with moderate improvements in both areas.
""",
    },
    {
        "name": "high_risk_expansion",
        "description": """
A company considers entering a new international market.

Option A: Aggressive expansion with high investment and high potential returns.
Option B: Moderate expansion with controlled investment and moderate returns.
Option C: No expansion, focusing on current market stability.
""",
    },
    {
        "name": "short_term_vs_long_term",
        "description": """
A company must choose between immediate profit and long-term positioning.

Option A: Maximize short-term profit by cutting R&D.
Option B: Maintain current balance between profit and R&D.
Option C: Increase R&D investment, reducing short-term profit but improving long-term innovation.
""",
    },
    {
        "name": "ethical_tradeoff",
        "description": """
A supplier offers significantly lower costs but has questionable labor practices.

Option A: Accept the supplier and reduce costs significantly.
Option B: Reject the supplier and maintain current ethical standards.
Option C: Work with the supplier under strict improvement conditions.
""",
    },
]


def run_suite():
    log_file = open("output/test_output.txt", "w")

    sys.stdout = Tee(sys.stdout, log_file)

    melchior = Melchior("openai/gpt-4o")
    balthasar = Balthasar("anthropic/claude-sonnet-4.5")
    casper = Casper("google/gemini-2.5-flash-lite")

    print("=" * 60)
    print("MAGI SYSTEM TEST SUITE")
    print("=" * 60)

    print("\nThis test runs multiple decision scenarios through the MAGI system.")
    print("Each scenario is evaluated by three specialized agents:")

    print("\nAgents:")
    print("- Melchior   → analytical / risk-balanced reasoning")
    print("- Balthasar  → human / ethical impact reasoning")
    print("- Casper     → strategic / pragmatic reasoning")

    print("\nModels used:")
    print("- Melchior   → openai/gpt-4o")
    print("- Balthasar  → anthropic/claude-3-sonnet")
    print("- Casper     → google/gemini-2.5-flash-lite")
    print("- Auditor    → openai/gpt-4o-mini")

    print("\nThe system will:")
    print("- Collect individual agent decisions")
    print("- Compute majority and weighted outcomes")
    print("- Run consistency checks and audits when needed")

    for scenario in SCENARIOS:
        print("\n" + "=" * 60)
        print(f"SCENARIO: {scenario['name']}")
        print("=" * 60)

        print("PROBLEM:")
        print(scenario["description"])

        results = {
            "Melchior": melchior.evaluate(scenario["description"]),
            "Balthasar": balthasar.evaluate(scenario["description"]),
            "Casper": casper.evaluate(scenario["description"]),
        }

        final = compare_agent_results(results, scenario)

        print(format_final_decision_report(final))
        print("")
        print(f"\nAgreement score: {final.agreement_score}")
        print("")
        print("Summary:")
        print(final.summary)

    print("\nTEST COMPLETED")

    sys.stdout = sys.__stdout__
    log_file.close()


run_suite()
