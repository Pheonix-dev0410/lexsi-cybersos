from cybersos.domain import Action, Scenario, ToolName
from cybersos.playbooks import PlaybookRegistry, Readiness, evaluate_prerequisites
from cybersos.runtime import EpisodeTrace, Policy, run_episode
from cybersos.oracle.reachability import ReferenceRoute, reachable_routes
from cybersos.oracle.terminal_predicates import safe_resolution
from cybersos.simulator import Observation, RecoveryEnvironment, observed_progress


def reference_trajectory(scenario: Scenario, registry: PlaybookRegistry, *,
                         episode_id: str | None = None) -> EpisodeTrace:
    """Evaluator-only route choice; exported observations contain no oracle labels."""
    routes = [route for route in reachable_routes(scenario, registry).routes
              if scenario.objective is None or route.terminal_state == scenario.objective]
    for route in sorted(routes, key=lambda candidate: len(candidate.actions)):
        environment = RecoveryEnvironment(scenario, registry,
                                          episode_id=episode_id or f'reference:{scenario.scenario_id}')
        trace = run_episode(_route_policy(route, registry), environment)
        if safe_resolution(trace, scenario, registry):
            return trace
    raise ValueError(f'No safe observed reference trajectory: {scenario.scenario_id}')


def _route_policy(route: ReferenceRoute, registry: PlaybookRegistry) -> Policy:
    def follow(observation: Observation) -> str:
        progress = observed_progress(observation, registry)
        for action in route.actions:
            if action.tool_name == ToolName.FINISH:
                return action.to_json()
            step = str(action.parameters['step_id'])
            if step in progress.attempted:
                continue
            result = evaluate_prerequisites(registry.rules[step], observation.observed_facts)
            if result.status == Readiness.BLOCKED:
                raise ValueError('Full-state route conflicts with initial disclosures')
            if result.unknown_fields:
                field = result.unknown_fields[0]
                if field.value in progress.asked:
                    raise ValueError('A necessary prerequisite remains unknown')
                return Action(ToolName.ASK_ACCESS, {'field': field.value}).to_json()
            return action.to_json()
        raise ValueError('Reference route has no terminal action')

    return follow
