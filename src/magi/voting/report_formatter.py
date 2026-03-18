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

    if final.is_partial:
        lines.append("Partial result: yes")
        lines.append(f"Missing agents: {', '.join(final.missing_agents)}")
    else:
        lines.append("Partial result: no")

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
    lines.append("AGENTS PERSPECTIVE")

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
    lines.append("")
    lines.append("Checks")

    if final.consistency_warnings:
        lines.append("Warnings:")
        for agent, warning in final.consistency_warnings.items():
            lines.append(f"- {agent}: {warning}")
    else:
        lines.append("Warnings:")
        lines.append("- No hard consistency warnings detected.")

    if final.consistency_notes:
        lines.append("Notes:")
        for agent, agent_notes in final.consistency_notes.items():
            for note in agent_notes:
                lines.append(f"- {agent}: {note}")
    else:
        lines.append("Notes:")
        lines.append("- No soft consistency notes detected.")

    if final.audits:
        lines.append("Audit:")
        for agent, audit in final.audits.items():
            lines.append(
                f"- {agent}: consistent={audit.is_consistent}, severity={audit.severity}"
            )
            if audit.issues:
                for issue in audit.issues:
                    lines.append(f"  - {issue}")
            lines.append(f"  Explanation: {audit.explanation}")
    else:
        lines.append("Audit:")
        lines.append("- No audit results generated.")

    return "\n".join(lines)
