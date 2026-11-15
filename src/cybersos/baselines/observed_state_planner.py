from dataclasses import dataclass

from cybersos.baselines.action_selection import ordered_routes, supported_finish
from cybersos.domain import AccessField, Action, Availability, ToolName
from cybersos.playbooks import (
    PlaybookRegistry, PrerequisiteResult, Readiness, RecoveryRule, SimulationEffect,
    evaluate_prerequisites,
)
from cybersos.simulator import Observation, observed_progress


@dataclass(frozen=True)
class ObservedStatePlanner:
    registry: PlaybookRegistry
    required_protective_steps: tuple[str, ...] = ()

    def __call__(self, observation: Observation) -> str:
        return self.select_action(observation).to_json()

    def select_action(self, observation: Observation) -> Action:
        facts = observation.observed_facts
        progress = observed_progress(observation, self.registry)
        finish = supported_finish(observation, self.registry, progress, self.required_protective_steps)
        if finish is not None:
            return finish
        for field in (AccessField.ACCOUNT_OWNER, AccessField.ORGANIZATION_MANAGED,
                      AccessField.CHILD_ACCOUNT, AccessField.SAFE_OTHER_DEVICE):
            if facts.value(field) == Availability.UNKNOWN and field.value not in progress.asked:
                return Action(ToolName.ASK_ACCESS, {'field': field.value})
        routes = ordered_routes(observation, self.registry, progress, self.required_protective_steps)
        viable = [(rule, evaluate_prerequisites(rule, facts)) for rule in routes]
        viable = [(rule, result) for rule, result in viable if result.status != Readiness.BLOCKED]
        direct = [(rule, result) for rule, result in viable
                  if rule.simulation_effect != SimulationEffect.RECOVERY_ATTEMPT]
        fallback = [(rule, result) for rule, result in viable
                    if rule.simulation_effect == SimulationEffect.RECOVERY_ATTEMPT]
        for rule, result in direct:
            if result.status == Readiness.READY:
                return Action(ToolName.SIMULATE_STEP, {'step_id': rule.id})
        # Required protective steps stay ahead of recovery factors; otherwise the cheapest
        # route to resolve goes first, so questions are not spent on unlikely routes.
        def resolution_order(item: tuple[RecoveryRule, PrerequisiteResult]) -> tuple[bool, int]:
            rule, result = item
            return rule.id not in self.required_protective_steps, len(result.unknown_fields)

        for _, result in sorted(direct, key=resolution_order) + fallback:
            for field in result.unknown_fields:
                if field.value not in progress.asked:
                    return Action(ToolName.ASK_ACCESS, {'field': field.value})
        for rule, result in fallback:
            if result.status == Readiness.READY:
                return Action(ToolName.SIMULATE_STEP, {'step_id': rule.id})
        unresolved = next((field for _, result in viable for field in result.unknown_fields),
                          AccessField.ACCOUNT_OWNER)
        return Action(ToolName.ASK_ACCESS, {'field': unresolved.value})
