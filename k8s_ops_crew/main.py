"""CLI entry-point for K8sOps Crew.

Usage:
    python -m k8s_ops_crew "Give me a health summary of the current cluster"

Or via the installed script:
    k8s-ops-crew "Give me a health summary"
"""

from __future__ import annotations

import logging
import sys
import uuid

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()
logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(name)s | %(message)s")


def main(intent: str | None = None) -> None:
    """Run the K8sOps Crew graph for the given intent and print the report.

    Args:
        intent: Natural-language intent string. Reads from sys.argv[1] if None.
    """
    # Lazy import so startup is fast when --help is used.
    from k8s_ops_crew.graph import build_graph
    from k8s_ops_crew.state import ClusterOpsState

    if intent is None:
        if len(sys.argv) < 2:
            console.print("[bold red]Usage:[/] k8s-ops-crew '<intent>'")
            sys.exit(1)
        intent = " ".join(sys.argv[1:])

    console.print(
        Panel(f"[bold cyan]K8sOps Crew[/] — Phase 1\n\n[italic]{intent}[/]", expand=False)
    )

    graph = build_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: ClusterOpsState = {  # type: ignore[assignment]
        "user_intent": intent,
        "messages": [],
        "plan": [],
        "cluster_snapshot": {},
        "analysis": {},
        "actions_proposed": [],
        "actions_approved": [],
        "report": "",
        "current_phase": "",
        "errors": [],
    }

    console.print("\n[dim]Streaming agent steps…[/]\n")

    final_state: ClusterOpsState | None = None
    for chunk in graph.stream(initial_state, config=config, stream_mode="values"):
        phase = chunk.get("current_phase", "")
        if phase:
            console.print(f"[bold green]▶ phase:[/] {phase}")
        final_state = chunk

    if final_state is None:
        console.print("[bold red]No output produced.[/]")
        sys.exit(1)

    report = final_state.get("report", "")
    errors = final_state.get("errors", [])

    console.print("\n")
    if report:
        console.print(Markdown(report))
    else:
        console.print("[yellow]No report generated.[/]")

    if errors:
        console.print("\n[bold red]Errors encountered:[/]")
        for err in errors:
            console.print(f"  [red]•[/] {err}")


if __name__ == "__main__":
    main()
