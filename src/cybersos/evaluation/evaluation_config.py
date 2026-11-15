from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cybersos.evaluation.auditkit_bridge import SCORER_VERSION
from cybersos.policy import ServingContract
from cybersos.serialization import load_strict_yaml


@dataclass(frozen=True)
class EvaluationConfig:
    seed: int
    case_count: int
    action_budget: int
    bootstrap_repetitions: int


def load_evaluation_config(path: Path, contract: ServingContract | None = None) -> EvaluationConfig:
    """Load the frozen protocol; when a serving contract is given, every shared setting must agree with it."""
    config = load_strict_yaml(path)
    if not isinstance(config, dict) or config.get('schema_version') != 'cybersos.eval.v1':
        raise ValueError('Expected evaluation config schema cybersos.eval.v1')
    for name in ('seed', 'case_count', 'action_budget', 'trials'):
        if type(config.get(name)) is not int or (name != 'seed' and config[name] < 1):
            raise ValueError(f'Invalid evaluation setting: {name}')
    if config.get('mode') != 'recorded' or config['trials'] != 1:
        raise ValueError('Only one recorded trial per case is supported')
    sections = {key: config.get(key) for key in ('decoding', 'protocol', 'bootstrap')}
    if not all(isinstance(value, dict) for value in sections.values()):
        raise ValueError('Evaluation decoding, protocol and bootstrap must be mappings')
    mismatches = [name for actual, wanted, name in _protocol_checks(config, sections) if actual != wanted]
    if contract is not None:
        mismatches += [name for actual, wanted, name in _values_that_must_match_contract(config, sections, contract.fields)
                       if actual != wanted]
    if mismatches:
        raise ValueError('Evaluation settings conflict with the frozen protocol: ' + ', '.join(mismatches))
    repetitions = sections['bootstrap'].get('repetitions')
    if type(repetitions) is not int or repetitions < 1:
        raise ValueError('bootstrap.repetitions must be positive')
    return EvaluationConfig(config['seed'], config['case_count'], config['action_budget'], repetitions)


def _protocol_checks(config: dict[str, Any], sections: dict[str, Any]) -> tuple[tuple[object, object, str], ...]:
    decoding, protocol, bootstrap = sections['decoding'], sections['protocol'], sections['bootstrap']
    return (
        (decoding.get('do_sample'), False, 'decoding.do_sample'),
        (decoding.get('seed'), config['seed'], 'decoding.seed'),
        (protocol.get('malformed_action_retries'), 0, 'protocol.malformed_action_retries'),
        (protocol.get('generated_answer_cache_for_latency'), False, 'protocol.generated_answer_cache_for_latency'),
        (protocol.get('frozen'), True, 'protocol.frozen'),
        (protocol.get('stop_tokens'), [], 'protocol.stop_tokens'),
        (protocol.get('post_processing'), 'strict_core_parser', 'protocol.post_processing'),
        (protocol.get('final_sweeps_per_checkpoint'), 1, 'protocol.final_sweeps_per_checkpoint'),
        (protocol.get('retrieval_cache_conditions'), 'equal', 'protocol.retrieval_cache_conditions'),
        (bootstrap.get('unit'), 'scenario_root', 'bootstrap.unit'),
        (bootstrap.get('confidence'), 0.95, 'bootstrap.confidence'),
        (config.get('scorer_version'), SCORER_VERSION, 'scorer_version'),
    )


def _values_that_must_match_contract(config: dict[str, Any], sections: dict[str, Any],
                     fields: Any) -> tuple[tuple[object, object, str], ...]:
    return (
        (config.get('action_budget'), fields['budgets']['actions'], 'action_budget'),
        (config.get('observation_mode'), fields['observations']['mode'], 'observation_mode'),
        (sections['decoding'].get('max_new_tokens'), fields['budgets']['generation_tokens'],
         'decoding.max_new_tokens'),
        (sections['protocol'].get('timeout_seconds'), fields['failure_policy']['timeout_seconds'],
         'protocol.timeout_seconds'),
    )
