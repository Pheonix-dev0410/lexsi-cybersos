from dataclasses import dataclass

from cybersos.app.app_assets import AppAssets
from cybersos.app.demo_cases import PROTECTIVE_STEPS
from cybersos.app.serving_policy import RULE_PLANNER, ServingModel, session_policy
from cybersos.domain import Incident, Provider, ProviderResponse, Scenario, SessionMode
from cybersos.runtime import EpisodeRunner, Policy
from cybersos.simulator import RecoveryEnvironment

ENTRY_INCIDENTS = {
    'account': (Provider.GOOGLE_PERSONAL, Incident.LOST_SECOND_FACTOR),
    'android': (Provider.ANDROID, Incident.LOST_PHONE),
    'exposed': (Provider.GOOGLE_PERSONAL, Incident.EXPOSED_PASSWORD),
}


@dataclass
class IncidentSession:
    runner: EpisodeRunner
    policy: Policy
    policy_label: str
    synthetic: bool = False
    required_steps: tuple[str, ...] = ()

    @property
    def environment(self) -> RecoveryEnvironment:
        return self.runner.environment

    def answer(self, value: str) -> None:
        self.environment.report_access(value)
        self.runner.run(self.policy)

    def report(self, value: str) -> None:
        """The environment decides whether a reported result completes the workflow."""
        self.environment.report_step(ProviderResponse(value))
        self.runner.run(self.policy)


def start_incident(assets: AppAssets, entry: str, serving: ServingModel = RULE_PLANNER,
                   *, demo_key: str | None = None) -> IncidentSession:
    if demo_key is not None:
        scenario = assets.demos[demo_key]
    else:
        provider, incident = ENTRY_INCIDENTS[entry]
        scenario = Scenario(
            'incident-guidance', provider, incident, True, {},
            opening_message='Structured incident guidance; availability answers only.',
            required_protective_steps=PROTECTIVE_STEPS if entry == 'exposed' else ())
    environment = RecoveryEnvironment(scenario, assets.registry, episode_id='private-session',
                                      mode=SessionMode.INCIDENT_GUIDANCE)
    policy = session_policy(serving, assets.registry, scenario.required_protective_steps)
    session = IncidentSession(EpisodeRunner(environment), policy, serving.label, synthetic=demo_key is not None,
                              required_steps=scenario.required_protective_steps)
    session.runner.run(policy)
    return session
