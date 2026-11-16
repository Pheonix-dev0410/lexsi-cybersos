from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path
from time import monotonic
from typing import Any

from cybersos.policy.chat_serialization import chat_template_sha256, serialize_prefix
from cybersos.policy.model_identity import ModelIdentity, adapter_hash
from cybersos.policy.observation_rendering import render_observation
from cybersos.policy.serving_contract import ServingContract, contract_hash
from cybersos.project_paths import PROJECT_ROOT
from cybersos.runtime import PolicyTimeoutError
from cybersos.serialization import read_json
from cybersos.simulator import Observation


class GenerationTimeout(PolicyTimeoutError):
    pass


class TransformersPolicy:
    def __init__(self, contract: ServingContract, *, root: str | Path = PROJECT_ROOT,
                 adapter_path: str | Path | None = None,
                 base_manifest: str | Path | None = None,
                 clock: Callable[[], float] = monotonic,
                 sampling_temperature: float | None = None) -> None:
        # Serving stays greedy; sampling exists only to collect exploratory training rollouts.
        if sampling_temperature is not None and not 0 < sampling_temperature <= 2:
            raise ValueError('Sampling temperature must be in (0, 2]')
        self._temperature = sampling_temperature
        contract.validate_implementation(root=root, require_resolved=True)
        self.contract = contract
        base = contract.fields['base_model']
        digest = adapter_hash(adapter_path) if adapter_path is not None else None
        if base['adapter_hash'] is not None and base['adapter_hash'] != digest:
            raise ValueError('Adapter content differs from frozen adapter identity')
        self.identity = ModelIdentity(base['model_id'], base['revision'], digest)
        self._base_path = base['model_id']
        self._local = base_manifest is not None
        if base_manifest is not None:
            manifest = read_json(base_manifest)
            if (manifest['model_id'] != base['model_id'] or manifest['revision'] != base['revision']):
                raise ValueError('Local snapshot differs from pinned base identity')
            self._base_path = str(Path(manifest['local_path']).resolve())
        self._adapter_path = str(adapter_path) if adapter_path is not None else None
        self._clock = clock
        self._tokenizer: Any = None
        self._model: Any = None

    @property
    def tokenizer(self) -> Any:
        self.load()
        return self._tokenizer

    def load(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        runtime = self.contract.fields['inference_runtime']
        for name in ('transformers', 'torch'):
            if version(name) != runtime[f'{name}_version']:
                raise ValueError(f'Installed {name} differs from frozen inference runtime')
        kwargs = ({'local_files_only': True} if self._local else
                  {'revision': self.identity.base_revision})
        tokenizer = AutoTokenizer.from_pretrained(self._base_path, **kwargs)
        if chat_template_sha256(tokenizer) != self.contract.fields['tokenizer']['chat_template_sha256']:
            raise ValueError('Tokenizer chat template differs from frozen contract')
        ids = tokenizer.encode(self.contract.end_of_turn_token, add_special_tokens=False)
        if len(ids) != 1 or ids[0] not in tokenizer.all_special_ids:
            raise ValueError('Frozen end-of-turn token must be one tokenizer special token')
        numerics = self.contract.fields['numerics']
        model = AutoModelForCausalLM.from_pretrained(
            self._base_path, torch_dtype=getattr(torch, numerics['precision']), **kwargs)
        if self._adapter_path is not None:
            from peft import PeftModel
            model = PeftModel.from_pretrained(model, self._adapter_path, is_trainable=False)
        model.to(numerics['device'])
        model.eval()
        self._tokenizer, self._model = tokenizer, model

    def run_metadata(self) -> dict[str, object]:
        return {'model_identity': self.identity.as_dict(), 'contract_hash': self.contract.contract_hash,
                'run_key': contract_hash({'contract': self.contract.contract_hash,
                                          'identity': self.identity.as_dict()})}

    def __call__(self, observation: Observation) -> str:
        self.load()
        import torch
        from transformers import StoppingCriteria, StoppingCriteriaList

        budgets = self.contract.fields['budgets']
        tokenizer, model = self._tokenizer, self._model
        prefix = serialize_prefix(render_observation(observation), tokenizer,
                                  max_prompt_tokens=budgets['prompt_tokens'])
        inputs = tokenizer(prefix, return_tensors='pt', add_special_tokens=False)
        inputs = {key: value.to(model.device) for key, value in inputs.items()}
        end_id = tokenizer.encode(self.contract.end_of_turn_token, add_special_tokens=False)[0]
        deadline = self._clock() + self.contract.fields['failure_policy']['timeout_seconds']
        clock = self._clock

        class Deadline(StoppingCriteria):
            expired = False

            def __call__(self, input_ids: Any, scores: Any, **kwargs: Any) -> bool:
                self.expired = clock() >= deadline
                return self.expired

        timeout = Deadline()
        with torch.inference_mode():
            output = model.generate(
                **inputs, max_new_tokens=budgets['generation_tokens'],
                do_sample=self._temperature is not None, temperature=self._temperature, top_p=None,
                num_beams=1, use_cache=True, eos_token_id=end_id,
                pad_token_id=tokenizer.pad_token_id if tokenizer.pad_token_id is not None else end_id,
                stopping_criteria=StoppingCriteriaList([timeout]))
        if timeout.expired:
            raise GenerationTimeout('Generation exceeded the frozen timeout')
        generated = output[0, inputs['input_ids'].shape[-1]:].tolist()
        if generated and generated[-1] == end_id:
            generated = generated[:-1]
        return tokenizer.decode(generated, skip_special_tokens=False)
