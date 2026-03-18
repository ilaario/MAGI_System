from collections import Counter, defaultdict

from magi.audit.consistency_auditor import ConsistencyAuditor
from magi.audit.model import ConsistencyAudit
from magi.models.decision_result import DecisionResult
from magi.models.final_decision import FinalDecision

EXPECTED_AGENTS = {"Melchior", "Balthasar", "Casper"}


def compute_agreement_score(results: dict[str, DecisionResult]) -> float:
    votes = [result.decision for result in results.values()]
    counter = Counter(votes)
    top_count = counter.most_common(1)[0][1]
    return round(top_count / len(votes), 2)


def compute_weighted_scores(results: dict[str, DecisionResult]) -> dict[str, int]:
    scores: dict[str, int] = defaultdict(int)

    for result in results.values():
        scores[result.decision] += result.confidence

    return dict(scores)


def should_request_recovery_round(
    results: dict[str, DecisionResult],
    is_partial: bool,
    vote_type: str,
) -> tuple[bool, str | None]:
    if len(results) < 2:
        return True, "Fewer than two valid agent outputs are available."

    if is_partial and len(results) == 2:
        votes = {result.decision for result in results.values()}
        if len(votes) == 2:
            return (
                True,
                "Panel is incomplete and the two available agents are split 1-1.",
            )

    if len(results) == 3 and vote_type == "split":
        return True, "All three agents returned different decisions."

    return False, None


def compare_agent_results(
    results: dict[str, DecisionResult], scenario: str
) -> FinalDecision:
    if not results:
        raise ValueError("compare_agent_results received no valid agent results.")

    present_agents = set(results.keys())
    missing_agents = sorted(EXPECTED_AGENTS - present_agents)
    is_partial = len(missing_agents) > 0

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

    weighted_scores = compute_weighted_scores(results)
    weighted_winner = max(weighted_scores, key=lambda k: weighted_scores[k])
    agreement_score = compute_agreement_score(results)

    needs_recovery_round, recovery_reason = should_request_recovery_round(
        results=results,
        is_partial=is_partial,
        vote_type=vote_type,
    )

    # If we have an unresolved/incomplete deadlock, do not pretend we have a real winner.
    if needs_recovery_round:
        final_decision = "UNRESOLVED"
        winning_agents = []
        dissenting_agents = list(results.keys())
    else:
        final_decision = top_decision
        winning_agents = [
            agent for agent, vote in votes.items() if vote == final_decision
        ]
        dissenting_agents = [
            agent for agent, vote in votes.items() if vote != final_decision
        ]

    consistency_warnings = detect_consistency_warnings(results)
    consistency_notes = detect_consistency_notes(results)

    audits = {}
    auditor = ConsistencyAuditor(model="openai/gpt-4o-mini")

    for agent_name, result in results.items():
        if should_audit_agent(
            agent_name, result, consistency_warnings, consistency_notes
        ):
            try:
                audits[agent_name] = auditor.audit(scenario, result)
            except Exception as e:
                audits[agent_name] = ConsistencyAudit(
                    supports_selected_option=False,
                    acknowledges_tradeoffs=False,
                    implicitly_supports_alternative=False,
                    reasoning_is_generic=True,
                    direct_contradiction_present=False,
                    is_consistent=False,
                    severity="high",
                    issues=[f"Audit failed: {e}"],
                    explanation="The auditor could not validate this output.",
                )

    summary = build_summary(
        final_decision=final_decision,
        vote_type=vote_type,
        results=results,
        winning_agents=winning_agents,
        dissenting_agents=dissenting_agents,
        weighted_scores=weighted_scores,
        weighted_winner=weighted_winner,
        consistency_warnings=consistency_warnings,
        needs_recovery_round=needs_recovery_round,
        recovery_reason=recovery_reason,
    )

    return FinalDecision(
        final_decision=final_decision,
        vote_type=vote_type,
        winning_agents=winning_agents,
        dissenting_agents=dissenting_agents,
        results=results,
        weighted_scores=weighted_scores,
        weighted_winner=weighted_winner,
        consistency_warnings=consistency_warnings,
        summary=summary,
        agreement_score=agreement_score,
        consistency_notes=consistency_notes,
        audits=audits,
        is_partial=is_partial,
        missing_agents=missing_agents,
        needs_recovery_round=needs_recovery_round,
        recovery_reason=recovery_reason,
    )


def detect_consistency_warnings(results: dict[str, DecisionResult]) -> dict[str, str]:
    warnings: dict[str, str] = {}

    negative_cues = {
        "A": [
            "high risk",
            "high risk of failure",
            "very high investment",
            "aggressive expansion",
            "substantial harm",
            "disproportionate burden",
            "large-scale negative consequences",
            "catastrophic",
            "overextended",
            "severe",
        ],
        "B": [
            "insufficient return",
            "limited gain",
            "moderate profit may be insufficient",
            "implementation challenges",
            "stagnation",
        ],
        "C": [
            "low profit",
            "stagnation",
            "missed growth",
            "forgo opportunities",
            "insufficient progress",
        ],
    }

    severe_risk_terms = [
        "high risk",
        "severe",
        "catastrophic",
        "disproportionate",
        "large-scale",
        "significant harm",
        "instability",
        "negative consequences",
    ]

    positive_claims = [
        "stability",
        "low risk",
        "manageable",
        "trust",
        "balanced",
        "preserves",
        "reduces harm",
        "minimizes harm",
        "controlled",
    ]

    for agent_name, result in results.items():
        selected = result.decision
        other_options = [opt for opt in ["A", "B", "C"] if opt != selected]

        reasoning_text = " ".join(result.reasoning).lower()
        risks_text = " ".join(result.risks).lower()
        full_text = f"{reasoning_text} {risks_text}"

        score = 0
        details = []

        if result.confidence <= 15:
            score += 1
            details.append(
                f"very low confidence in selected option ({result.confidence})"
            )
        elif result.confidence <= 30:
            details.append(f"low confidence in selected option ({result.confidence})")

        matched_negative = [
            cue for cue in negative_cues.get(selected, []) if cue in full_text
        ]
        if len(matched_negative) >= 2:
            score += 1
            details.append(
                f"negative cues about selected option {selected}: {', '.join(sorted(set(matched_negative)))}"
            )

        praise_other_option = []
        for other in other_options:
            patterns = [
                f"option {other.lower()} balances",
                f"option {other.lower()} preserves",
                f"option {other.lower()} avoids",
                f"option {other.lower()} reduces",
                f"option {other.lower()} supports",
                f"option {other.lower()} minimizes",
                f"{other.lower()} balances",
                f"{other.lower()} preserves",
                f"{other.lower()} avoids",
                f"{other.lower()} reduces",
                f"{other.lower()} supports",
                f"{other.lower()} minimizes",
            ]
            for pattern in patterns:
                if pattern in reasoning_text:
                    praise_other_option.append(pattern)

        if praise_other_option:
            score += 1
            details.append(
                f"reasoning appears to favor another option: {', '.join(sorted(set(praise_other_option)))}"
            )

        matched_severe_risks = [
            term for term in severe_risk_terms if term in risks_text
        ]
        matched_positive_claims = [
            term for term in positive_claims if term in reasoning_text
        ]

        if matched_positive_claims and matched_severe_risks:
            score += 1
            details.append(
                f"reasoning emphasizes safety/stability but risks remain severe: {', '.join(sorted(set(matched_severe_risks)))}"
            )

        explicit_anchor_patterns = [
            f"option {selected.lower()}",
            f"{selected.lower()} ",
        ]
        if not any(pattern in reasoning_text for pattern in explicit_anchor_patterns):
            details.append(
                f"reasoning does not clearly anchor itself to selected option {selected}"
            )

        if score > 0:
            warnings[agent_name] = f"[score={score}] " + " | ".join(details)

    return warnings


def detect_consistency_notes(
    results: dict[str, DecisionResult],
) -> dict[str, list[str]]:
    notes: dict[str, list[str]] = {}

    generic_terms = [
        "stability",
        "trust",
        "balanced",
        "flexibility",
        "positioning",
        "growth",
        "impact",
        "capability",
        "resilience",
        "advantage",
    ]

    scenario_specific_terms = [
        "layoff",
        "automation",
        "privacy",
        "security",
        "data",
        "expansion",
        "market",
        "r&d",
        "innovation",
        "supplier",
        "labor",
        "ethical",
        "cost",
        "worker",
        "profit",
    ]

    for agent_name, result in results.items():
        agent_notes: list[str] = []

        reasoning_text = " ".join(result.reasoning).lower()
        assumptions_text = " ".join(result.assumptions).lower()

        if result.confidence <= 15:
            agent_notes.append(f"very low confidence ({result.confidence})")
        elif result.confidence <= 30:
            agent_notes.append(f"low confidence ({result.confidence})")

        selected = result.decision.lower()
        anchor_patterns = [
            f"option {selected}",
            f"{selected} ",
        ]

        specific_hits = [
            term for term in scenario_specific_terms if term in reasoning_text
        ]
        if (
            not any(pattern in reasoning_text for pattern in anchor_patterns)
            and len(specific_hits) == 0
        ):
            agent_notes.append("reasoning is weakly anchored to the selected option")

        generic_hits = [term for term in generic_terms if term in reasoning_text]
        if len(generic_hits) >= 2 and len(specific_hits) == 0:
            agent_notes.append("reasoning may be overly generic")

        speculative_markers = [
            "market conditions",
            "leadership values",
            "stakeholders value",
            "industry rewards",
            "current market remains stable",
            "future competitiveness",
        ]
        speculative_hits = [m for m in speculative_markers if m in assumptions_text]
        if len(speculative_hits) >= 1:
            agent_notes.append("assumptions may be somewhat speculative")

        if agent_notes:
            notes[agent_name] = agent_notes

    return notes


def build_summary(
    final_decision: str,
    vote_type: str,
    results: dict[str, DecisionResult],
    winning_agents: list[str],
    dissenting_agents: list[str],
    weighted_scores: dict[str, int],
    weighted_winner: str,
    consistency_warnings: dict[str, str],
    needs_recovery_round: bool,
    recovery_reason: str | None,
) -> str:
    sentences: list[str] = []

    if len(results) < 3:
        missing = EXPECTED_AGENTS - set(results.keys())
        if missing:
            sentences.append(
                f"This result is partial because the following agent(s) did not return valid outputs: {', '.join(sorted(missing))}."
            )

    if needs_recovery_round:
        sentences.append(
            f"No final MAGI decision is available yet because a recovery round is required. {recovery_reason}"
        )
    elif vote_type == "unanimous":
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
    sentences.append(
        f"Weighted support was {weighted_text}, with {weighted_winner} currently leading."
    )

    if consistency_warnings:
        flagged = ", ".join(consistency_warnings.keys())
        sentences.append(f"Consistency warnings were raised for {flagged}.")

    return "\n".join(sentences)


def should_audit_agent(
    agent_name: str,
    result: DecisionResult,
    consistency_warnings: dict[str, str],
    consistency_notes: dict[str, list[str]],
) -> bool:
    if agent_name in consistency_warnings:
        return True

    if agent_name in consistency_notes and len(consistency_notes[agent_name]) >= 2:
        return True

    if result.confidence <= 30:
        return True

    return False
