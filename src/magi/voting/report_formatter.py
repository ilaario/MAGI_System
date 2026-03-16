from magi.models.final_decision import FinalDecision


def _format_score_map(weighted_scores: dict[str, int]) -> str:
    return ", ".join(
        f"{decision}={score}" for decision, score in sorted(weighted_scores.items())
    )


def _short_reason(result) -> str:
    if not result.reasoning:
        return "No reasoning provided."
    return result.reasoning[0]


def format_final_decision_report(final: FinalDecision) -> str:
    lines: list[str] = []

    lines.append("MAGI DECISION REPORT")
    lines.append("")
    lines.append(f"Scenario outcome: {final.final_decision}")
    lines.append(f"Decision mode: {final.vote_type}")
    lines.append(f"Agreement score: {final.agreement_score:.2f}")
    lines.append(f"Weighted support: {_format_score_map(final.weighted_scores)}")
    lines.append("")

    lines.append("Why this option won")
    for agent in final.winning_agents:
        result = final.results[agent]
        lines.append(f"- {agent}: {_short_reason(result)}")

    if final.dissenting_agents:
        lines.append("")
        lines.append("Dissent")
        for agent in final.dissenting_agents:
            result = final.results[agent]
            lines.append(
                f"- {agent}: chose {result.decision} ({result.confidence}) because {_short_reason(result).lower()}"
            )

    lines.append("")
    lines.append("Agent perspectives")

    for agent_name, result in final.results.items():
        lines.append("")
        lines.append(f"{agent_name}")
        lines.append(f"Decision: {result.decision} ({result.confidence})")

        lines.append("Why:")
        for item in result.reasoning:
            lines.append(f"- {item}")

        lines.append("Risks:")
        for item in result.risks:
            lines.append(f"- {item}")

        lines.append("Assumptions:")
        for item in result.assumptions:
            lines.append(f"- {item}")

    lines.append("")
    lines.append("Notes")
    if final.consistency_warnings:
        for agent, warning in final.consistency_warnings.items():
            lines.append(f"- {agent}: {warning}")
    else:
        lines.append("- No consistency warnings detected.")

    return "\n".join(lines)
