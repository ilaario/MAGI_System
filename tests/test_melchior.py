from magi.agents.melchior import Melchior

scenario = """
A company must choose one of three strategies for the next 12 months:

Option A:
Expand aggressively into a new market.
Potential profit: high
Risk of failure: high
Upfront investment: very high

Option B:
Improve current operations and reduce inefficiencies.
Potential profit: moderate
Risk of failure: low
Upfront investment: moderate

Option C:
Freeze expansion and conserve cash.
Potential profit: low
Risk of failure: very low
Upfront investment: low

Choose exactly one option.
"""

agent = Melchior(model="openrouter/free")
result = agent.evaluate(scenario)

print(result.model_dump_json(indent=2))
