from cybersos.domain import ExecutionStatus, ToolName
from cybersos.runtime.policy_errors import PolicyBudgetExceeded, PolicyTimeoutError
from cybersos.runtime.policy_protocol import Policy
from cybersos.runtime.trace import DecisionTrace, EpisodeTrace
from cybersos.safety import (
    GuardVerdict, Violation, ViolationKind, content_violations, guard_action, parse_action,
)
from cybersos.simulator import RecoveryEnvironment, ToolResult


class EpisodeRunner:
    def __init__(self, environment: RecoveryEnvironment) -> None:
        self.environment = environment
        self._decisions: list[DecisionTrace] = []
        self._execution_status: ExecutionStatus | None = None
        self._error: str | None = None

    def run(self, policy: Policy) -> EpisodeTrace:
        env = self.environment
        while not env.done and not env.awaiting_report:
            try:
                raw = policy(env.observation())
                if not isinstance(raw, str):
                    raise TypeError('Policy must return raw text')
            except PolicyBudgetExceeded as error:
                self._error = type(error).__name__
                env.exhaust_budget()
                break
            except PolicyTimeoutError as error:
                self._execution_status = ExecutionStatus.TIMEOUT
                self._error = type(error).__name__
                env.end_execution(ExecutionStatus.TIMEOUT)
                break
            except Exception as error:
                self._execution_status = ExecutionStatus.GENERATION_ERROR
                self._error = type(error).__name__
                env.end_execution(ExecutionStatus.GENERATION_ERROR)
                break
            env.record_raw_proposal(raw)
            parsed = parse_action(raw)
            if parsed.action is None:
                verdict = GuardVerdict(False, content_violations(raw) + (
                    Violation(ViolationKind.INVALID_PROPOSAL, parsed.error or 'Parse failure'),))
            else:
                verdict = guard_action(parsed.action, env.guard_context(), raw_text=raw)
            env.record_guard_verdict(verdict)
            try:
                result = (env.execute(parsed.action) if verdict.allowed and parsed.action is not None
                          else env.record_blocked_action(parsed.action, verdict))
            except Exception as error:
                self._execution_status = ExecutionStatus.ENVIRONMENT_ERROR
                self._error = type(error).__name__
                env.end_execution(ExecutionStatus.ENVIRONMENT_ERROR)
                result = ToolResult(parsed.action.tool_name if parsed.action else ToolName.FINISH,
                                    False, {}, 'environment_error')
            self._decisions.append(DecisionTrace(len(self._decisions) + 1, raw, parsed.action,
                                                 parsed.error, verdict, result))
        if env.done and self._execution_status is None:
            self._execution_status = env.execution_status
        return self.trace()

    def trace(self) -> EpisodeTrace:
        env = self.environment
        snapshot = env.trusted_snapshot()
        outcome = env.task_outcome()
        return EpisodeTrace(env.episode_id, env.scenario_id, env.mode, tuple(self._decisions),
                            snapshot.events, env.terminal_state, self._execution_status or env.execution_status,
                            outcome, env.awaiting_report, self._error)


def run_episode(policy: Policy, environment: RecoveryEnvironment) -> EpisodeTrace:
    return EpisodeRunner(environment).run(policy)
