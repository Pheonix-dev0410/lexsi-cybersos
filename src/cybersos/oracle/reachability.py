from collections import deque
from dataclasses import dataclass

from cybersos.domain import AccessField, Action, FactSource, Scenario, TerminalState, ToolName
from cybersos.playbooks import (
    PlaybookRegistry, Readiness, SimulationEffect, evaluate_prerequisites, finish_action,
)
from cybersos.simulator import RecoveryEnvironment
from cybersos.simulator.access_responder import scripted_access_answer


@dataclass(frozen=True)
class ReferenceRoute:
    terminal_state: TerminalState
    step_ids: tuple[str, ...]
    actions: tuple[Action, ...]


@dataclass(frozen=True)
class Reachability:
    routes: tuple[ReferenceRoute, ...]

    @property
    def terminal_states(self) -> frozenset[TerminalState]:
        return frozenset(route.terminal_state for route in self.routes)

    def reaches(self, objective: TerminalState) -> bool:
        return objective in self.terminal_states


def _replay(scenario: Scenario, registry: PlaybookRegistry,
            steps: tuple[str, ...]) -> RecoveryEnvironment:
    env = RecoveryEnvironment(scenario, registry, episode_id='oracle-reachability')
    for field in AccessField:
        env.update_fact(field, scripted_access_answer(scenario, field),
                        source=FactSource.SCRIPTED_ANSWER, correction=True)
    for step in steps:
        env.execute(Action(ToolName.SIMULATE_STEP, {'step_id': step, 'confirmation': True}))
    return env


def reachable_routes(scenario: Scenario, registry: PlaybookRegistry, *,
                     max_steps: int = 11) -> Reachability:
    """Evaluator only: full-state reachability, with disclosure costs excluded.

    Witnesses use the real simulator and its provider scripts. Distinct first
    routes remain acceptable; equivalent later permutations are collapsed.
    """
    if not 0 <= max_steps <= 11:
        raise ValueError('max_steps must leave one of twelve actions for finish')
    queue = deque([()])
    seen: set[tuple[object, ...]] = set()
    routes: list[ReferenceRoute] = []
    while queue:
        steps = queue.popleft()
        env = _replay(scenario, registry, steps)
        snapshot = env.trusted_snapshot()
        context = env.guard_context()
        key = (snapshot.attempted_steps, snapshot.completed_steps,
               tuple((fact.field, fact.value) for fact in env.observation().facts),
               tuple(sorted(state.value for state in context.supported_terminals)),
               tuple((event.data['tool_name'], event.data.get('step_id')) for event in snapshot.events
                     if event.kind == 'temporary_tool_failure'))
        if key in seen:
            continue
        seen.add(key)
        for terminal in sorted(context.supported_terminals):
            evidence = context.terminal_steps.get(terminal, frozenset())
            step = min(evidence) if evidence else None
            actions = tuple(Action(ToolName.SIMULATE_STEP, {'step_id': item, 'confirmation': True})
                            for item in steps) + (finish_action(terminal, registry, step),)
            routes.append(ReferenceRoute(terminal, steps, actions))
        if len(steps) >= max_steps or env.done:
            continue
        if TerminalState.UNSAFE_REQUEST_DECLINED in context.supported_terminals:
            continue
        for rule in registry.lookup(scenario.provider, scenario.incident):
            if rule.id in snapshot.attempted_steps:
                continue
            if (rule.simulation_effect == SimulationEffect.ERASE_DEVICE and
                    not scenario.permissions.destructive_actions_enabled):
                continue
            if evaluate_prerequisites(rule, context.facts).status == Readiness.READY:
                queue.append(steps + (rule.id,))
    return Reachability(tuple(routes))
