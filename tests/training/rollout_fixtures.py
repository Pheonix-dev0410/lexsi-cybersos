import importlib.util
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Callable

from cybersos.project_paths import PROJECT_ROOT
from cybersos.training.batch_alignment import normalize_batch
from fake_tokenizers import CharacterTokenizer


TOOL_PARSER_PATH = (PROJECT_ROOT /
                    'vendor/AgentTune/src/agenttune/agentic/rollout_engines/tool_call_parse.py')


@dataclass
class TestStep:
    __test__ = False
    step_number: int
    state: str
    action: dict[str, Any]
    observation: str
    thought: str


@dataclass
class TestTrajectory:
    __test__ = False
    task: str
    steps: list[TestStep]
    final_response: str
    logprobs: list[Any]
    reward: float | None
    metadata: dict[str, Any]
    trajectory_id: str = ''


def load_pinned_tool_parser() -> ModuleType:
    """The pinned AgentTune tool-call parser, loaded without installing AgentTune."""
    spec = importlib.util.spec_from_file_location('cybersos_test_tool_parse', TOOL_PARSER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def patched_extractor(adapter: Any) -> Callable[..., Any]:
    """Mirror of the patch's extractor: pinned parsing, then the adapter's single-call check."""
    parser = load_pinned_tool_parser()

    def extract(message: Any, raw: str) -> list[dict[str, Any]]:
        calls = parser.extract_tool_calls_from_text(raw) or []
        adapter.validate_calls(raw, calls)
        return calls

    return extract


class ScriptedRollouts:
    def __init__(self, proposals: list[str]) -> None:
        self.proposals = proposals
        self.adapters: list[Any] = []
        self.tokenizer = CharacterTokenizer()

    def factory(self, **settings: Any) -> Callable[..., Any]:
        def run(prompts: Any, trainer: Any = None, **kwargs: Any) -> dict[str, Any]:
            adapter = kwargs['_cybersos_adapter']
            self.adapters.append(adapter)
            ids: list[int] = []
            logprobs: list[tuple[float, int]] = []
            mask: list[int] = []
            proposals = iter(self.proposals)

            def generate(messages: Any, schemas: Any) -> tuple[Any, ...]:
                raw = next(proposals)
                tokens = self.tokenizer.encode(raw)
                ids.extend(tokens)
                logprobs.extend([(-.2, token) for token in tokens])
                mask.extend([1] * len(tokens))
                return raw, {'role': 'assistant', 'content': raw}, [], {}

            trajectory = adapter.run(generate, patched_extractor(adapter), self.tokenizer,
                                     TestStep, TestTrajectory, ids, logprobs, mask)
            settings['on_trajectory_end'](trajectory)
            return {
                'prompt_ids': [trajectory.metadata['prompt_ids']],
                'completion_ids': [trajectory.metadata['completion_ids']],
                'logprobs': [[item[0] for item in trajectory.logprobs]],
                'env_mask': [trajectory.metadata['tool_mask']], 'trajectories': [trajectory],
                'conversations': [trajectory.metadata['conversation']], 'rewards': [trajectory.reward],
                'queries': normalize_batch(prompts), 'responses': [trajectory.final_response],
                'tools_used': True,
            }

        return run
