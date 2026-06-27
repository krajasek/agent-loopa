"""loopa generate — new code from a task description."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated, Optional

import typer

from agent_loopa.cli.display import (
    console,
    render_iteration_panel,
    render_parallel_panel,
    render_summary,
)
from agent_loopa.config.loader import default_config, load_config
from agent_loopa.models.messages import AgentOutput
from agent_loopa.orchestrator.orchestrator import Orchestrator, RunMode
from agent_loopa.orchestrator.pipeline import PARALLEL_STAGES, PipelineStage


def generate_command(
    task: Annotated[str, typer.Option("--task", "-t", help="Task description for code generation")],
    lang: Annotated[str, typer.Option("--lang", "-l", help="Target language")] = "python",
    output: Annotated[Path, typer.Option("--output", "-o", help="Output directory")] = Path("./output"),
    config_path: Annotated[Optional[Path], typer.Option("--config", "-c", help="TOML config file")] = None,
    max_iterations: Annotated[int, typer.Option("--max-iterations", "-n", help="Max refinement iterations")] = 3,
) -> None:
    """Generate production-quality code from a task description."""
    asyncio.run(_run(task, lang, output, config_path, max_iterations))


async def _run(
    task: str,
    lang: str,
    output: Path,
    config_path: Path | None,
    max_iterations: int,
) -> None:
    if config_path:
        cfg = load_config(config_path)
    else:
        cfg = default_config()

    cfg = cfg.model_copy(update={"output_dir": str(output), "gate": cfg.gate.model_copy(update={"max_iterations": max_iterations})})

    orchestrator = Orchestrator(config=cfg)

    # Collect outputs for display
    iteration_outputs: list[AgentOutput] = []
    parallel_outputs: list[AgentOutput] = []
    current_iteration = 0
    last_gate_reason = ""

    parallel_agent_names = {s.value for s in PARALLEL_STAGES}

    async def on_output(out: AgentOutput) -> None:
        nonlocal current_iteration
        if out.agent_name in parallel_agent_names:
            parallel_outputs.append(out)
        else:
            if out.iteration != current_iteration:
                if iteration_outputs:
                    console.print(render_iteration_panel(current_iteration, max_iterations, iteration_outputs, last_gate_reason))
                iteration_outputs.clear()
                current_iteration = out.iteration
            iteration_outputs.append(out)

    console.rule("[bold blue]agent-loopa[/bold blue] — generate mode")
    console.print(f"Task: [cyan]{task}[/cyan]  |  Language: [cyan]{lang}[/cyan]\n")

    result = await orchestrator.run(
        mode=RunMode.GENERATE,
        task_description=task,
        language=lang,
        on_agent_output=on_output,
    )

    # Print final iteration panel
    if iteration_outputs:
        console.print(render_iteration_panel(current_iteration, max_iterations, iteration_outputs, ""))

    # Print parallel panel
    if parallel_outputs:
        console.print(render_parallel_panel(parallel_outputs))

    # Save output files
    if result.final_code:
        code_dir = output / (result.final_code.filename.split(".")[0])
        code_dir.mkdir(parents=True, exist_ok=True)
        (code_dir / result.final_code.filename).write_text(result.final_code.content, encoding="utf-8")
        if result.test_suite:
            for tf in result.test_suite.test_files:
                (code_dir / tf.filename).write_text(tf.content, encoding="utf-8")
        if result.documentation and result.documentation.readme_section:
            (code_dir / "docs.md").write_text(result.documentation.readme_section, encoding="utf-8")

    render_summary(result, str(output))
