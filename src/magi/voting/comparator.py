from collections import Counter, defaultdict

from magi.models.decision_result import DecisionResult
from magi.models.final_decision import FinalDecision


def compute_agreement_score(results: dict[str, DecisionResult]) -> float:
    votes = [result.decision for result in results.values()]
    counter = Counter(votes)
    top_count = counter.most_common(1)[0][1]
    return round(top_count / len(votes), 2)


NEGATIVE_PATTERNS = {
    "A": [
        "high risk of failure",
        "aggressive expansion",
        "very high investment",
        "significant loss",
        "catastrophic loss",
    ],
    "B": [
        "limited returns",
        "moderate profit may be insufficient",
        "implementation challenges",
    ],
    "C": [
        "low profit",
        "stagnation",
        "forgo valuable improvements",
    ],
}


def compare_agent_results(results: dict[str, DecisionResult]) -> FinalDecision:
    votes = {agent: result.decision for agent, result in results.items()}
    counter = Counter(votes.values())

    most_common = counter.most_common()
    top_decision, top_count = most_common[0]

    if top_count == len(results):
        vote_type = "unanimous"
    elif top_count > 1:
        vote_type = "majority"
    else:
        vote_type = "split"

    winning_agents = [agent for agent, vote in votes.items() if vote == top_decision]
    dissenting_agents = [agent for agent, vote in votes.items() if vote != top_decision]

    weighted_scores = compute_weighted_scores(results)
    weighted_winner = max(weighted_scores, key=weighted_scores.get)

    agreement_score = compute_agreement_score(results)

    consistency_warnings = detect_consistency_warnings(results)

    summary = build_summary(
        final_decision=top_decision,
        vote_type=vote_type,
        results=results,
        winning_agents=winning_agents,
        dissenting_agents=dissenting_agents,
        weighted_scores=weighted_scores,
        weighted_winner=weighted_winner,
        consistency_warnings=consistency_warnings,
    )

    return FinalDecision(
        final_decision=top_decision,
        vote_type=vote_type,
        winning_agents=winning_agents,
        dissenting_agents=dissenting_agents,
        results=results,
        weighted_scores=weighted_scores,
        weighted_winner=weighted_winner,
        consistency_warnings=consistency_warnings,
        summary=summary,
        agreement_score=agreement_score,
    )


def compute_weighted_scores(results: dict[str, DecisionResult]) -> dict[str, int]:
    scores: dict[str, int] = defaultdict(int)

    for result in results.values():
        scores[result.decision] += result.confidence

    return dict(scores)


def detect_consistency_warnings(results: dict[str, DecisionResult]) -> dict[str, str]:
    warnings: dict[str, str] = {}

    for agent_name, result in results.items():
        text = " ".join(result.reasoning + result.risks).lower()
        selected = result.decision

        patterns = NEGATIVE_PATTERNS.get(selected, [])
        matched = [p for p in patterns if p in text]

        if len(matched) >= 2:
            warnings[agent_name] = (
                f"Selected option {selected} but used multiple negative cues about it: "
                + ", ".join(matched)
            )

    return warnings


def build_summary(
    final_decision: str,
    vote_type: str,
    results: dict[str, DecisionResult],
    winning_agents: list[str],
    dissenting_agents: list[str],
    weighted_scores: dict[str, int],
    weighted_winner: str,
    consistency_warnings: dict[str, str],
) -> str:
    sentences: list[str] = []

    if vote_type == "unanimous":
        sentences.append(f"All agents converged on {final_decision}.")
    elif vote_type == "majority":
        dissent_text = ", ".join(dissenting_agents)
        sentences.append(f"{final_decision} won by majority vote.")
        sentences.append(f"Dissent came from {dissent_text}.")
    else:
        sentences.append(
            f"No full convergence emerged, but {final_decision} was selected as the leading option."
        )

    for agent in winning_agents:
        reasoning = results[agent].reasoning
        if reasoning:
            first_reason = reasoning[0].strip()
            if first_reason and not first_reason.endswith("."):
                first_reason += "."
            sentences.append(
                f"{agent} emphasized that {first_reason[0].lower() + first_reason[1:]}"
            )

    weighted_text = ", ".join(
        f"{decision}={score}" for decision, score in sorted(weighted_scores.items())
    )
    sentences.append(f"Weighted support was {weighted_text}.")

    if consistency_warnings:
        flagged = ", ".join(consistency_warnings.keys())
        sentences.append(f"Consistency warnings were raised for {flagged}.")

    return "\n".join(sentences)
