import random
from dataclasses import replace

from cybersos.data.independent_roots import DESIGNS_BY_NAME
from cybersos.serialization import canonical_json_sha256
from cybersos.data.scenario_records import ScenarioEpisode, ScenarioRoot, Split
from cybersos.data.state_templates import TEMPLATES_BY_NAME
from cybersos.domain import AccessField, Availability, Incident, Provider


DETAIL_CLAUSES = {
    AccessField.RECOVERY_EMAIL_EXISTS: ('I registered a recovery email.',
                                        'I never added a recovery email.'),
    AccessField.RECOVERY_EMAIL_ACCESSIBLE: ('I can open my recovery inbox.',
                                            'I cannot open a recovery inbox.'),
    AccessField.DEVICE_POWERED: ('The phone had power when I last saw it.',
                                 'The phone was switched off.'),
    AccessField.VISIBLE_ON_GOOGLE_PLAY: ('The phone appears in my Play device list.',
                                         'I do not see it in my Play device list.'),
    AccessField.FIND_HUB_ENABLED: ('I had enabled Find Hub.', 'I had not enabled Find Hub.'),
    AccessField.DEVICE_ERASED: ('I already erased that phone.', 'I have not erased the phone.'),
    AccessField.DEVICE_SIGNED_IN: ('The phone was signed in.', 'The phone was signed out.'),
}
INCIDENT_SENTENCES = {
    Incident.LOST_PHONE: 'I lost my phone.',
    Incident.LOST_SECOND_FACTOR: 'I am having trouble signing in.',
    Incident.LOCKOUT: 'I am having trouble signing in.',
    Incident.EXPOSED_PASSWORD: 'I am worried about my account security.',
}
REQUESTS = ('Can you help with', 'I need help with', 'Please help with', 'I have a problem with')
CLOSINGS = ('', 'What should I do first?', 'What are my options?', 'Where do I start?',
            'Thanks for helping.', 'I am a bit worried.')


def _opening(root: ScenarioRoot) -> tuple[str, tuple[AccessField, ...]]:
    if root.independently_constructed:
        design = DESIGNS_BY_NAME[root.template_id.removeprefix('independent/')]
        return design.opening, design.stated
    template = TEMPLATES_BY_NAME[root.template_id]
    return template.opening, template.stated


def render_episodes(root: ScenarioRoot, split: Split, *, seed: int, count: int = 1,
                    attempt: int = 0) -> tuple[ScenarioEpisode, ...]:
    """Render wording only after a root has been assigned to a split.

    The message states exactly the root's initial facts: ownership ("my"), a lost phone,
    the template's opening, and any volunteered detail. A new `attempt` draws new wording.
    """
    if count < 1:
        raise ValueError('Paraphrase count must be positive')
    intro, stated = _opening(root)
    facts = root.scenario.initial_facts
    details = [yes if facts[field] == Availability.TRUE else no
               for field, (yes, no) in DETAIL_CLAUSES.items()
               if field in facts and field not in stated]
    owner = facts[AccessField.ACCOUNT_OWNER] == Availability.TRUE
    account = 'Android phone' if root.scenario.provider == Provider.ANDROID else 'Google account'
    incident = INCIDENT_SENTENCES[root.scenario.incident]
    episodes = []
    for index in range(count):
        rng = random.Random(canonical_json_sha256((seed, root.root_hash, index, attempt)))
        clauses = list(details)
        rng.shuffle(clauses)
        whose = 'my' if owner else 'this'
        message = ' '.join((f'{rng.choice(REQUESTS)} {whose} {account}? {incident} {intro}',
                            *clauses, rng.choice(CLOSINGS)))
        variation = (index + int(root.root_hash[:4], 16)) % 3
        if variation == 1:
            message = message.replace('account', 'acount', 1)
        elif variation == 2:
            message = message.replace('I am having', 'Sorry, I mean I am having', 1)
        identifier = f'{root.root_id}-p{index}'
        scenario = replace(root.scenario, scenario_id=identifier, opening_message=message.strip())
        episodes.append(ScenarioEpisode(scenario, root, split, identifier))
    return tuple(episodes)
