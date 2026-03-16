from magi.agents.casper import Casper

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

agent = Casper(model="openrouter/free")
result = agent.evaluate(scenario)

print(result.model_dump_json(indent=2))
