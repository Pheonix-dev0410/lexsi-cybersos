import sys
from pathlib import Path

from cybersos.safety import parse_action
from cybersos.training.adapter_checks import adapter_configuration, model_configuration
from cybersos.training.model_identity_checks import read_adapter_metadata


def verify_reload(path: str | Path) -> None:
    import torch
    from peft import AutoPeftModelForCausalLM
    from transformers import AutoTokenizer

    root = Path(path)
    expected = read_adapter_metadata(root)
    dtype = getattr(torch, expected['torch_dtype'])
    model = AutoPeftModelForCausalLM.from_pretrained(
        str(root), is_trainable=False, local_files_only=True, torch_dtype=dtype)
    tokenizer = AutoTokenizer.from_pretrained(str(root), local_files_only=True)
    if model_configuration(model) != expected['model_configuration']:
        raise RuntimeError('Fresh-process base configuration differs')
    if adapter_configuration(model) != expected['adapter_configuration']:
        raise RuntimeError('Fresh-process adapter revision or rank differs')
    model.to('cuda').eval()
    inputs = tokenizer(expected['smoke_prefix'], return_tensors='pt',
                       add_special_tokens=False).to('cuda')
    # Training set the tokenizer's EOS to the contract's end-of-response token; stop there as serving does.
    with torch.inference_mode():
        generated = model.generate(**inputs, max_new_tokens=expected['generation_tokens'],
                                   do_sample=False, eos_token_id=tokenizer.eos_token_id,
                                   pad_token_id=tokenizer.eos_token_id)
    text = tokenizer.decode(generated[0, inputs.input_ids.shape[-1]:], skip_special_tokens=True)
    if parse_action(text).action is None:
        raise RuntimeError(f'Reload smoke generation did not produce one valid tool action: {text[:300]!r}')
    print('Fresh-process adapter reload and valid-action generation passed')


if __name__ == '__main__':
    verify_reload(sys.argv[1])
