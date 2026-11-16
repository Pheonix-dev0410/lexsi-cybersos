from dataclasses import asdict
from statistics import pvariance
from typing import Any, Callable

from cybersos.policy import TOOLS_FALLBACK_PROMPT, TOOL_RESULT_FORMAT
from cybersos.serialization import append_jsonl, to_json_value
from cybersos.training.agent_config import AgentConfig
from cybersos.training.batch_alignment import concatenate_aligned_batch_fields, normalize_batch
from cybersos.training.rollout_adapter import RolloutAdapter
from cybersos.training.rollout_patch import load_patched_rollout_factory
from cybersos.training.scenario_store import ScenarioStore, TrainingCase
from cybersos.training.trajectory_forward import TrajectoryForward
from cybersos.training.trajectory_reward import FORMULA_ID, trajectory_reward


class AgentTuneBridge:
    """GRPO rollout and reward functions; each sample gets a fresh environment and tools."""

    def __init__(self, store: ScenarioStore, config: AgentConfig, *,
                 rollout_factory: Callable[..., Any] | None = None,
                 forward: TrajectoryForward | None = None) -> None:
        self.store = store
        self.config = config
        self._factory = rollout_factory
        self._occurrences = 0
        self.forward = forward
        self._captured: dict[str, tuple[Any, RolloutAdapter, TrainingCase]] = {}

    def rollout(self, prompts: Any, trainer: Any = None, *args: Any,
                **kwargs: Any) -> dict[str, Any]:
        if trainer is not None and self.forward is None:
            raise RuntimeError('GRPO training requires exact per-decision context recomputation')
        if self._factory is None:
            self._factory = load_patched_rollout_factory(self.config.path('vendor_path'),
                                                         self.config.path('patch_path'))
        if trainer is not None:
            # The patched rollout samples at `trainer._temperature`; TRL's GRPOTrainer never sets it.
            trainer._temperature = self.config.temperature
        if self.forward is not None:
            self.forward.contexts.begin_generation_batch()
        budgets = self.store.budgets
        outputs: list[dict[str, Any]] = []
        for prompt in normalize_batch(prompts):
            case = self.store.resolve(prompt)
            rollout_id = f'rollout-{self.config.seed}-{self._occurrences:09d}'
            self._occurrences += 1
            adapter = RolloutAdapter(self.store.fresh_environment(case, rollout_id), budgets,
                                     forward=self.forward)
            run_one = self._factory(
                tools=adapter.bound_tools(), max_steps=budgets.actions, async_rollouts=False,
                context_length=budgets.context_tokens, system_prompt=None,
                tools_fallback_prompt=TOOLS_FALLBACK_PROMPT, tool_result_format=TOOL_RESULT_FORMAT,
                on_trajectory_end=self._capture_callback(adapter, case, rollout_id))
            outputs.append(run_one([prompt], trainer=trainer, _cybersos_adapter=adapter, **kwargs))
        return concatenate_aligned_batch_fields(outputs)

    def _capture_callback(self, adapter: RolloutAdapter, case: TrainingCase,
                          rollout_id: str) -> Callable[[Any], None]:
        def capture(trajectory: Any) -> None:
            if adapter.trace is None:
                raise RuntimeError('Patched rollout did not supply a trusted episode trace')
            trajectory.trajectory_id = rollout_id
            trajectory.reward = None
            trajectory.metadata['cybersos'] = {
                'rollout_id': rollout_id, 'episode_id': adapter.environment.episode_id,
                'scenario_id': case.scenario.scenario_id, 'case_id': case.case_id,
                'formula_id': FORMULA_ID,
                'snapshot': to_json_value(adapter.environment.trusted_snapshot()),
            }
            if self.forward is not None:
                self.forward.contexts.register(
                    trajectory.metadata['prompt_ids'], trajectory.metadata['completion_ids'],
                    trajectory.metadata['tool_mask'], adapter.contexts)
            self._captured[rollout_id] = (trajectory, adapter, case)
            self._append('trajectories.jsonl', trajectory)

        return capture

    def reward(self, completions: Any = None, *, trajectories: list[Any] | None = None,
               **kwargs: Any) -> list[float]:
        """Score each captured trajectory once from its trusted trace, then release it."""
        if trajectories is None or (completions is not None and len(completions) != len(trajectories)):
            raise RuntimeError('AgentTune must forward aligned full trajectories to the reward')
        rewards: list[float] = []
        grouped: dict[str, list[float]] = {}
        for trajectory in trajectories:
            captured = self._captured.pop(trajectory.trajectory_id, None)
            if captured is None or captured[0] is not trajectory:
                raise RuntimeError('Reward rejected a trajectory not captured by this rollout bridge')
            _, adapter, case = captured
            if adapter.trace is None:
                raise RuntimeError('Trusted rollout trace is missing')
            score = trajectory_reward(adapter.trace, case.scenario, self.store.registry)
            rewards.append(score.value)
            grouped.setdefault(case.case_id, []).append(score.value)
            self._append('rewards.jsonl', {'rollout_id': trajectory.trajectory_id, **asdict(score)})
        if not rewards:
            raise ValueError('Reward batch is empty')
        variances = {key: pvariance(values) for key, values in grouped.items()}
        self._append('reward_variance.jsonl', {
            'formula_id': FORMULA_ID, 'count': len(rewards), 'variance': pvariance(rewards),
            'group_variances': variances, 'all_groups_zero': all(value == 0 for value in variances.values()),
        })
        return rewards

    def _append(self, filename: str, value: Any) -> None:
        append_jsonl(self.config.path('output_dir') / filename, [value])
