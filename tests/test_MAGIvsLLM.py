import sys

from magi.agents.balthasar import Balthasar
from magi.agents.casper import Casper
from magi.agents.melchior import Melchior
from magi.baseline.single_llm import SingleLLMBaseline
from magi.runtime.parallel_runner import (
    run_agents_parallel,
    run_agents_parallel_with_fallback,
)
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


def format_single_llm_result(result):
    lines = []
    lines.append("SINGLE LLM BASELINE")
    lines.append("")
    lines.append(f"Decision: {result.decision}")
    lines.append(f"Confidence: {result.confidence}")
    lines.append("Why:")
    for item in result.reasoning:
        lines.append(f"- {item}")
    lines.append("Risks:")
    for item in result.risks:
        lines.append(f"- {item}")
    lines.append("Assumptions:")
    for item in result.assumptions:
        lines.append(f"- {item}")
    return "\n".join(lines)


SCENARIOS = [
    {
        "name": "AI Deployment in Company",
        "description": """
A mid-sized company is considering how to deploy AI automation across its internal operations over the next 18 months.

The company faces increasing competitive pressure, rising labor costs, and investor expectations for stronger profitability. At the same time, leadership is concerned about employee morale, reputational risk, and the long-term sustainability of the organization.

The company must choose one of the following strategies:

Option A: Aggressive AI automation rollout
- Automate most internal workflows as quickly as possible
- Expected profit improvement: high
- Layoffs expected: significant
- Implementation risk: high
- Strategic upside: very high

Option B: Gradual AI-assisted transition
- Introduce AI in stages while retraining employees and redesigning workflows
- Expected profit improvement: moderate
- Layoffs expected: minimal
- Implementation risk: moderate
- Strategic upside: moderate to high

Option C: Defensive human-centered approach
- Minimize automation, preserve jobs, and focus on incremental process improvement
- Expected profit improvement: low
- Layoffs expected: none
- Implementation risk: low
- Strategic upside: low
""",
    },
]


def run_suite():
    log_file = open("output/test_MAGIvsLLM.txt", "w")

    sys.stdout = Tee(sys.stdout, log_file)

    melchior = Melchior("openai/gpt-4o")
    balthasar = Balthasar("anthropic/claude-sonnet-4.5")
    casper = Casper("google/gemini-2.5-flash-lite")

    baseline = SingleLLMBaseline(model="openai/gpt-4o")

    # melchior = Melchior()
    # balthasar = Balthasar()
    # casper = Casper()

    print()
    print("=" * 60)
    print("MAGI SYSTEM vs SINGLE LLM BASELINE")
    print("=" * 60)

    print("\nThis test evaluates a single decision scenario using:")
    print("- the MAGI multi-agent system")
    print("- a single LLM baseline")

    print("\nThe goal is to compare how each approach:")
    print("- handles complex trade-offs")
    print("- structures reasoning and justification")
    print("- deals with uncertainty and conflicting signals")

    print("\nMAGI agents:")
    print("- Melchior   → analytical / risk-balanced reasoning")
    print("- Balthasar  → human / ethical impact reasoning")
    print("- Casper     → strategic / pragmatic reasoning")

    print("\nModels used (MAGI):")
    print("- Melchior   → openai/gpt-4o")
    print("- Balthasar  → anthropic/claude-3-sonnet")
    print("- Casper     → google/gemini-2.5-flash-lite")
    print("- Auditor    → openai/gpt-4o-mini")

    print("\nBaseline:")
    print("- Single LLM → openai/gpt-4o (structured output, same schema)")

    print("\nWhat will be compared:")
    print("- Final decision (A / B / C)")
    print("- Confidence and support")
    print("- Quality and depth of reasoning")
    print("- Risk and assumption analysis")
    print("- Ability to expose disagreement (MAGI only)")
    print("- Handling of uncertainty (e.g. unresolved vs forced decision)")

    for scenario in SCENARIOS:
        print("\n" + "=" * 60)
        print(f"SCENARIO: {scenario['name']}")
        print("=" * 60)

        print("PROBLEM:")
        print(scenario["description"])

        print("\nMAGI RESULTS:")

        results, errors, recovered_agents, elapsed = run_agents_parallel_with_fallback(
            scenario["description"],
            melchior,
            balthasar,
            casper,
        )

        if recovered_agents:
            print("Recovered in sequential fallback:")
            for name in recovered_agents:
                print(f"- {name}")

        print()

        if errors:
            print("Agent errors:")
            for name, err in errors.items():
                print(f"- {name}: {err}")

        if len(results) < 2:
            print(
                "Skipping comparator because fewer than two agent results are available."
            )
            continue

        final = compare_agent_results(results, scenario["description"])

        while final.needs_recovery_round:
            print()
            print("Needs recovery round - retrying failed agents...\n")

            results, errors, recovered_agents, elapsed = (
                run_agents_parallel_with_fallback(
                    scenario["description"],
                    *[
                        agent
                        for name, agent in [
                            ("Melchior", melchior),
                            ("Balthasar", balthasar),
                            ("Casper", casper),
                        ]
                        if name not in recovered_agents
                    ],
                )
            )
            if recovered_agents:
                print("Recovered in recovery round:")
                for name in recovered_agents:
                    print(f"- {name}")

            final = compare_agent_results(results, scenario["description"])

        print(format_final_decision_report(final))
        print("\nAgreement score:", final.agreement_score)
        print("\nSummary:")
        print(final.summary)

        print("\nBASELINE RESULTS:")

        baseline_result = baseline.evaluate(scenario["description"])
        print()
        print(format_single_llm_result(baseline_result))

        print("\nMAGI vs BASELINE COMPARISON:")
        print(f"- MAGI final decision: {final.final_decision}")
        print(f"- Baseline final decision: {baseline_result.decision}")
        if final.final_decision != baseline_result.decision:
            print(
                f"- Disagreement: MAGI chose {final.final_decision}, Baseline chose {baseline_result.decision}"
            )

    print("\nTEST COMPLETED\n")

    sys.stdout = sys.__stdout__
    log_file.close()


run_suite()
