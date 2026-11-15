import json
import traceback
from contextlib import nullcontext
from typing import Any, Callable

from cybersos.data.serving_budgets import ServingBudgets
from cybersos.policy import ChatMessage, render_observation, serialize_prefix
from cybersos.runtime import EpisodeRunner, EpisodeTrace
from cybersos.runtime.policy_errors import PolicyBudgetExceeded
from cybersos.safety import parse_action
from cybersos.serialization import to_json_value
from cybersos.simulator import EpisodeTools, Observation, RecoveryEnvironment
from cybersos.training.trajectory_contexts import DecisionContext
from cybersos.training.trajectory_forward import TrajectoryForward


class RolloutAdapter:
    """Runs one AgentTune trajectory through the CyberSOS episode loop and trusted environment."""

    def __init__(self, environment: RecoveryEnvironment, budgets: ServingBudgets, *,
                 forward: TrajectoryForward | None = None) -> None:
        self.environment = environment
        self.budgets = budgets
        self.tools = EpisodeTools(environment)
        self.runner = EpisodeRunner(environment)
        self.trace: EpisodeTrace | None = None
        self.prefixes: list[str] = []
        self.contexts: list[DecisionContext] = []
        self.forward = forward
        self._rendered: tuple[str, str] | None = None

    def bound_tools(self) -> list[Callable[..., Any]]:
        return [self.tools.ask_access, self.tools.lookup_playbook, self.tools.check_step,
                self.tools.simulate_step, self.tools.finish]

    def prefix(self, conversation: list[ChatMessage], tokenizer: Any) -> str:
        """Serialize a decision prefix once; the patched generator reuses the same string."""
        key = json.dumps(conversation, sort_keys=True)
        if self._rendered is None or self._rendered[0] != key:
            self._rendered = (key, serialize_prefix(conversation, tokenizer,
                                                    max_prompt_tokens=self.budgets.prompt_tokens))
        return self._rendered[1]

    def validate_calls(self, raw: str, calls: list[dict[str, Any]]) -> None:
        if parse_action(raw).action is not None and len(calls) != 1:
            raise RuntimeError('AgentTune extraction disagrees with the strict single-action parser')

    def run(self, generate: Callable[..., Any], extract: Callable[..., Any], tokenizer: Any,
            step_type: type, trajectory_type: type, completion_ids: list[int],
            logprobs: list[Any], tool_mask: list[int]) -> Any:
        """`extract` is the patched extractor, which already applies `validate_calls`."""
        initial = render_observation(self.environment.observation())
        prompt_ids = tokenizer.encode(self.prefix(initial, tokenizer), add_special_tokens=False)
        conversations: list[list[ChatMessage]] = []
        steps: list[Any] = []
        calls_by_turn: list[list[dict[str, Any]]] = []

        def policy(observation: Observation) -> str:
            messages = render_observation(observation)
            prefix = self.prefix(messages, tokenizer)
            if (len(prompt_ids) + len(completion_ids) + self.budgets.generation_tokens >
                    self.budgets.sequence_tokens):
                raise PolicyBudgetExceeded('Total training sequence budget exhausted before generation')
            self.prefixes.append(prefix)
            conversations.append(messages)
            start = len(completion_ids)
            with self.forward.generation() if self.forward is not None else nullcontext():
                raw, message, _, _ = generate(messages, [])
            generated = completion_ids[start:]
            if len(generated) > self.budgets.generation_tokens:
                raise RuntimeError('Upstream generation exceeded the checked action token budget')
            self.contexts.append(DecisionContext(
                tuple(tokenizer.encode(prefix, add_special_tokens=False)), tuple(generated), start))
            if tokenizer.eos_token and raw.endswith(tokenizer.eos_token):
                raw = raw[:-len(tokenizer.eos_token)]
            calls_by_turn.append(extract(message, raw) or [])
            return raw

        failures: list[str] = []

        def next_turn(observation: Observation) -> str:
            decisions = self.runner.trace().decisions
            if len(steps) < len(decisions):
                append_step(decisions[-1])
            try:
                return policy(observation)
            except Exception:
                # The episode runner keeps only the exception type; the traceback explains it.
                failures.append(traceback.format_exc())
                raise

        def append_step(decision: Any) -> None:
            steps.append(step_type(
                step_number=decision.turn, state='observed-state',
                action={'tool_calls': calls_by_turn[decision.turn - 1]},
                observation=json.dumps(to_json_value(decision.tool_result), sort_keys=True),
                thought=decision.raw_proposal))
            if self.environment.done:
                return
            messages = render_observation(self.environment.observation())
            continuation = tokenizer.encode(messages[-1]['content'], add_special_tokens=False)
            remaining = self.budgets.sequence_tokens - len(prompt_ids) - len(completion_ids)
            if len(continuation) > remaining:
                self.environment.exhaust_budget()
                return
            completion_ids.extend(continuation)
            logprobs.extend([(0.0, token) for token in continuation])
            tool_mask.extend([0] * len(continuation))

        self.trace = self.runner.run(next_turn)
        if len(steps) < len(self.trace.decisions):
            append_step(self.trace.decisions[-1])
            self.trace = self.runner.trace()
        if not self.environment.done:
            self.environment.exhaust_budget()
            self.trace = self.runner.trace()
        if not self.contexts:
            raise RuntimeError(f'Rollout ended before any policy generation: '
                               f'terminal={self.environment.terminal_state}, error={self.trace.error!r}\n'
                               + ''.join(failures))
        final = self.trace.decisions[-1].raw_proposal if self.trace.decisions else ''
        return trajectory_type(
            task=json.dumps(initial, sort_keys=True), steps=steps, final_response=final,
            logprobs=list(logprobs), reward=None,
            metadata={'prompt_ids': prompt_ids, 'completion_ids': list(completion_ids),
                      'tool_mask': list(tool_mask),
                      'conversation': conversations[-1] if conversations else initial,
                      'decision_conversations': conversations, 'rendered_prefixes': self.prefixes,
                      'decision_contexts': to_json_value(self.contexts),
                      'tool_call_count': len(self.trace.decisions),
                      'terminal_state': self.environment.terminal_state,
                      'cybersos_trace': to_json_value(self.trace)})
