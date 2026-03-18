import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

FRAMES = [
    "[o---------]",
    "[-o--------]",
    "[--o-------]",
    "[---o------]",
    "[----o-----]",
    "[-----o----]",
    "[------o---]",
    "[-------o--]",
    "[--------o-]",
    "[---------o]",
    "[--------o-]",
    "[-------o--]",
    "[------o---]",
    "[-----o----]",
    "[----o-----]",
    "[---o------]",
    "[--o-------]",
    "[-o--------]",
]

AGENT_ORDER = ["Melchior", "Balthasar", "Casper"]


def _render_agent_line(name: str, state: str, frame: str = "", detail: str = "") -> str:
    if state == "running":
        return f"{name:<10} {frame} - Running"
    if state == "done":
        return f"{name:<10} [##########] - Done!"
    if state == "failed":
        return f"{name:<10} [!!!!!!!!!!] - Failed!"
    if state == "retrying":
        suffix = f" {detail}" if detail else ""
        return f"{name:<10} {frame} - Retrying{suffix}"
    if state == "recovered":
        return f"{name:<10} [##########] - Recovered!"
    return f"{name:<10} [..........] - Idle"


def _draw_states(states, frame_index: int):
    lines = []
    for agent in AGENT_ORDER:
        state = states[agent]["state"]
        detail = states[agent].get("detail", "")
        frame = (
            FRAMES[frame_index % len(FRAMES)]
            if state in {"running", "retrying"}
            else ""
        )
        lines.append(_render_agent_line(agent, state, frame, detail))
    return "\n".join(lines)


def _multi_agent_loader(stop_event, states):
    first_draw = True
    frame_index = 0

    while not stop_event.is_set():
        output = _draw_states(states, frame_index)

        if first_draw:
            sys.stdout.write(output + "\n")
            sys.stdout.flush()
            first_draw = False
        else:
            sys.stdout.write("\x1b[3F")  # up 3 lines
            sys.stdout.write("\x1b[J")  # clear to end
            sys.stdout.write(output + "\n")
            sys.stdout.flush()

        time.sleep(0.12)
        frame_index += 1

    # final redraw, static
    final_lines = []
    for agent in AGENT_ORDER:
        state = states[agent]["state"]
        detail = states[agent].get("detail", "")
        final_lines.append(_render_agent_line(agent, state, "", detail))

    sys.stdout.write("\x1b[3F")
    sys.stdout.write("\x1b[J")
    sys.stdout.write("\n".join(final_lines) + "\n")
    sys.stdout.flush()


def _countdown_inline(agent_name: str, states, seconds: int):
    for remaining in range(seconds, 0, -1):
        states[agent_name]["state"] = "retrying"
        states[agent_name]["detail"] = f"in {remaining}s"
        time.sleep(1)
    states[agent_name]["detail"] = ""


def run_agents_parallel(scenario: str, melchior, balthasar, casper):
    start = time.perf_counter()

    agents = {
        "Melchior": melchior,
        "Balthasar": balthasar,
        "Casper": casper,
    }

    states = {
        "Melchior": {"state": "running", "detail": ""},
        "Balthasar": {"state": "running", "detail": ""},
        "Casper": {"state": "running", "detail": ""},
    }

    results = {}
    errors = {}

    stop_event = threading.Event()
    loader_thread = threading.Thread(
        target=_multi_agent_loader,
        args=(stop_event, states),
        daemon=True,
    )
    loader_thread.start()

    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                name: executor.submit(agent.evaluate, scenario)
                for name, agent in agents.items()
            }

            for name, future in futures.items():
                try:
                    results[name] = future.result()
                    states[name]["state"] = "done"
                except Exception as e:
                    errors[name] = str(e)
                    states[name]["state"] = "failed"
    finally:
        stop_event.set()
        loader_thread.join()

    elapsed = time.perf_counter() - start
    print(f"Parallel execution finished in {elapsed:.2f}s")

    return results, errors, elapsed


def run_agents_parallel_with_fallback(scenario: str, melchior, balthasar, casper):
    start = time.perf_counter()

    agents = {
        "Melchior": melchior,
        "Balthasar": balthasar,
        "Casper": casper,
    }

    states = {
        "Melchior": {"state": "running", "detail": ""},
        "Balthasar": {"state": "running", "detail": ""},
        "Casper": {"state": "running", "detail": ""},
    }

    results = {}
    errors = {}
    failed_agents = []
    recovered_agents = []

    stop_event = threading.Event()
    loader_thread = threading.Thread(
        target=_multi_agent_loader,
        args=(stop_event, states),
        daemon=True,
    )
    loader_thread.start()

    try:
        # First pass: parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                name: executor.submit(agent.evaluate, scenario)
                for name, agent in agents.items()
            }

            for name, future in futures.items():
                try:
                    results[name] = future.result()
                    states[name]["state"] = "done"
                except Exception as e:
                    errors[name] = f"[parallel] {e}"
                    failed_agents.append(name)
                    states[name]["state"] = "failed"

        # Second pass: sequential fallback
        for name in failed_agents:
            _countdown_inline(name, states, 3)

            try:
                states[name]["state"] = "retrying"
                states[name]["detail"] = ""
                results[name] = agents[name].evaluate(scenario, retries=1)
                errors.pop(name, None)
                recovered_agents.append(name)
                states[name]["state"] = "recovered"
            except Exception as e:
                errors[name] = f"{errors[name]} | [fallback] {e}"
                states[name]["state"] = "failed"
                states[name]["detail"] = ""

    finally:
        stop_event.set()
        loader_thread.join()

    total_elapsed = time.perf_counter() - start
    print(f"Total execution time: {total_elapsed:.2f}s")

    return results, errors, recovered_agents, total_elapsed
