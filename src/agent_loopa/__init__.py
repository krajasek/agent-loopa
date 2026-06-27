"""agent-loopa — Multi-agent SDLC harness.

Public API::

    from agent_loopa import Orchestrator, PipelineConfig, RunMode

    config = PipelineConfig.from_toml("configs/default_pipeline.toml")
    orchestrator = Orchestrator(config=config)

    result = await orchestrator.run(
        mode=RunMode.GENERATE,
        task_description="Implement a rate limiter using token bucket",
        language="python",
    )

    print(result.final_code.content)
    print(result.test_suite.test_files[0].content)
    print(result.audit_log_path)
"""

from agent_loopa.config.schema import PipelineConfig
from agent_loopa.orchestrator.orchestrator import Orchestrator, OrchestratorResult, RunMode
from agent_loopa.version import __version__

__all__ = [
    "Orchestrator",
    "OrchestratorResult",
    "PipelineConfig",
    "RunMode",
    "__version__",
]
