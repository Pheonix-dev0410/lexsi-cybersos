from dataclasses import dataclass

from cybersos.baselines.action_selection import ordered_routes, supported_finish
from cybersos.baselines.questionnaire_flows import QUESTION_FLOWS
from cybersos.domain import AccessField, Action, Availability, Incident, Provider, ToolName
from cybersos.playbooks import PlaybookRegistry, Readiness, SimulationEffect, evaluate_prerequisites
from cybersos.simulator import Observation, observed_progress


@dataclass(frozen=True)
class GuidedQuestionnaire:
    """Fixed branching availability controls; corrections enter through trusted intake."""

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
        routes = ordered_routes(observation, self.registry, progress, self.required_protective_steps)
        evaluated = [(rule, evaluate_prerequisites(rule, facts)) for rule in routes]
        ready_steps = {rule.id for rule, result in evaluated if result.status == Readiness.READY}
        flow = QUESTION_FLOWS.get((Provider(observation.provider), Incident(observation.incident)), ())
        for section in flow:
            if any(facts.value(branch.field) == branch.answer for branch in section.skip_if):
                continue
            for question in section.questions:
                if any(facts.value(branch.field) == branch.answer for branch in question.skip_if):
                    continue
                if (facts.value(question.field) == Availability.UNKNOWN and
                        question.field.value not in progress.asked):
                    return Action(ToolName.ASK_ACCESS, {'field': question.field.value})
            if ready_steps.intersection(section.recommend_steps):
                break
        for fallback in (False, True):
            for rule, result in evaluated:
                if (result.status == Readiness.READY and
                        (rule.simulation_effect == SimulationEffect.RECOVERY_ATTEMPT) == fallback):
                    return Action(ToolName.SIMULATE_STEP, {'step_id': rule.id})
        # No limitation can be certified while a prerequisite is unknown, so ask for one.
        unresolved = next((field for _, result in evaluated if result.status != Readiness.BLOCKED
                           for field in result.unknown_fields), AccessField.ACCOUNT_OWNER)
        return Action(ToolName.ASK_ACCESS, {'field': unresolved.value})
