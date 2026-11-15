from pathlib import Path
from time import monotonic
from typing import Any

from cybersos.policy import TransformersPolicy
from cybersos.serialization import canonical_json_sha256, file_sha256


class MeasuredModelPolicy(TransformersPolicy):
    """Counts real `generate()` calls and tokens, and refuses to run unless the intended weights are active.

    Base and adapter runs share this class so prompt, parser and decoding cannot differ between them.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.counters = {'generation_calls': 0, 'cache_hits': 0, 'input_tokens': 0, 'output_tokens': 0,
                         'unmeasured_output_calls': 0}
        self.cold_loading_seconds = 0.0
        self.generation_seconds = 0.0
        self.loaded_identity: dict[str, object] = {'verified': False, 'fresh_process': False}
        self._instrumented = False

    def load_for_check(self) -> dict[str, object]:
        self.load()
        return self.loaded_identity

    def load(self) -> None:
        if self._instrumented:
            return
        started = monotonic()
        super().load()
        model = self._model
        active = getattr(model, 'active_adapter', None)
        peft_configs = getattr(model, 'peft_config', {})
        if self._adapter_path is not None and (not active or active not in peft_configs):
            raise ValueError('The intended adapter is not active after loading')
        if self._adapter_path is None and peft_configs:
            raise ValueError('Base run unexpectedly loaded an adapter')
        self.loaded_identity = {'verified': True, 'fresh_process': False,
                                'identity': self.identity.as_dict(), 'active_adapter': active,
                                'adapter_path': str(Path(self._adapter_path).resolve())
                                if self._adapter_path is not None else None}
        if self._local:
            snapshot = Path(self._base_path)
            weights = sorted((*snapshot.glob('*.safetensors'), *snapshot.glob('pytorch_model*.bin')))
            if not weights:
                raise ValueError('The pinned local base snapshot contains no weight files')
            weight_hashes = {path.name: file_sha256(path) for path in weights}
            self.loaded_identity['base_weight_files'] = weight_hashes
            self.loaded_identity['base_weight_sha256'] = canonical_json_sha256(weight_hashes)
        else:
            self.loaded_identity['base_weight_sha256'] = None
            self.loaded_identity['base_weight_hash_status'] = 'unmeasured; supply a local --base-manifest'
        generate = model.generate

        def measured_generate(*args: Any, **kwargs: Any) -> Any:
            self.counters['generation_calls'] += 1
            prompt_tokens = int(kwargs['input_ids'].shape[-1])
            self.counters['input_tokens'] += prompt_tokens
            call_started = monotonic()
            try:
                output = generate(*args, **kwargs)
                self.counters['output_tokens'] += int(output.shape[-1]) - prompt_tokens
                return output
            except Exception:
                self.counters['unmeasured_output_calls'] += 1
                raise
            finally:
                self.generation_seconds += monotonic() - call_started

        model.generate = measured_generate
        self._instrumented = True
        self.cold_loading_seconds = monotonic() - started
