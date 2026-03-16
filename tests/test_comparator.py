from magi.agents.balthasar import Balthasar
from magi.agents.casper import Casper
from magi.agents.melchior import Melchior
from magi.voting.comparator import compare_agent_results
from magi.voting.report_formatter import format_final_decision_report

scenario = """
A company must choose one of three strategies for the next 12 months.

A:
Expand aggressively into a new market.
Potential profit: high
Risk of failure: high
Upfront investment: very high

B:
Improve current operations and reduce inefficiencies.
Potential profit: moderate
Risk of failure: low
Upfront investment: moderate

C:
Freeze expansion and conserve cash.
Potential profit: low
Risk of failure: very low
Upfront investment: low

Choose exactly one option: A, B, or C.
"""

print(scenario)

print("MAGI System is evaluating...")
results = {
    "Melchior": Melchior(model="openrouter/free").evaluate(scenario),
    "Balthasar": Balthasar(model="openrouter/free").evaluate(scenario),
    "Casper": Casper(model="openrouter/free").evaluate(scenario),
}

final = compare_agent_results(results)

print(format_final_decision_report(final))
print("")
print("Summary:")
print(final.summary)
