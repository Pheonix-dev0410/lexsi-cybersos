from pathlib import Path

from cybersos.data.decision_gates import DecisionGates, check_export_count
from cybersos.data.decision_rows import Record, Row, row_hash
from cybersos.data.serving_budgets import ServingBudgets
from cybersos.data.token_boundaries import split_token_ids
from cybersos.playbooks import PlaybookRegistry
from cybersos.policy import ChatTokenizer, PromptBudgetExceeded, chat_template_sha256, export_sft_example
from cybersos.serialization import canonical_json_sha256, read_json, read_jsonl, write_json, write_jsonl


def render_training_file(curated_dir: str | Path, output_path: str | Path,
                         registry: PlaybookRegistry, tokenizer: ChatTokenizer,
                         budgets: ServingBudgets, *, end_of_turn_token: str | None = None,
                         tokenizer_name: str = 'provided tokenizer') -> Record:
    directory, destination = Path(curated_dir), Path(output_path)
    rows = read_jsonl(directory / 'sft_alpaca.jsonl')
    provenance = read_json(directory / 'provenance.json')
    curation = read_json(directory / 'curation_manifest.json')
    check_export_count(curation['accepted_rows'], rows)
    if not rows:
        raise ValueError('Empty curated dataset')
    if {row_hash(row) for row in rows} != set(curation['content_hashes']):
        raise ValueError('curated_content_changed')
    gates = DecisionGates(read_jsonl(directory / 'trajectories.jsonl'), registry)
    rendered: list[Row] = []
    mapping: list[Record] = []
    rejections: list[Record] = []
    for row in rows:
        digest = row_hash(row)
        origins = provenance.get(digest, [])
        if errors := gates.check(row, origins):
            rejections.append({'content_hash': digest, 'reasons': errors})
            continue
        origin = origins[0]
        observation = gates.replay(origin['trajectory_id']).observations[origin['turn']]
        try:
            example = export_sft_example(
                observation, row['output'], tokenizer, max_prompt_tokens=budgets.prompt_tokens,
                max_completion_tokens=budgets.generation_tokens, end_of_turn_token=end_of_turn_token)
            prompt_ids, completion_ids = split_token_ids(
                example['prompt'], example['completion'], tokenizer, budgets)
        except (ValueError, PromptBudgetExceeded) as error:
            rejections.append({'content_hash': digest, 'reasons': [str(error)]})
            continue
        result = {'instruction': example['prompt'], 'input': '', 'output': example['completion']}
        rendered.append(result)
        mapping.append({'rendered_hash': row_hash(result), 'canonical_hash': digest,
                        'origins': origins, 'prompt_tokens': len(prompt_ids),
                        'completion_tokens': len(completion_ids),
                        'sequence_tokens': len(prompt_ids) + len(completion_ids)})
    manifest = {'input_rows': len(rows), 'fitted_rows': len(rendered),
                'accepted_rows': len(rendered) if not rejections else 0,
                'exported_rows': len(rendered) if not rejections else 0,
                'rejected_rows': len(rejections), 'tokenizer': tokenizer_name,
                'chat_template_sha256': chat_template_sha256(tokenizer),
                'end_of_turn_token': end_of_turn_token or tokenizer.eos_token,
                'max_prompt_tokens': budgets.prompt_tokens,
                'max_completion_tokens': budgets.generation_tokens,
                'max_sequence_tokens': budgets.context_tokens,
                'status': 'failed' if rejections else 'passed',
                'output_path': str(destination), 'content_hash': canonical_json_sha256(rendered)}
    write_jsonl(destination.parent / 'render_rejections.jsonl', rejections)
    write_json(destination.parent / 'render_manifest.json', manifest)
    if rejections:
        raise ValueError(f'{len(rejections)} rendering rejections; no training file published')
    check_export_count(curation['accepted_rows'], rendered)
    write_jsonl(destination, rendered)
    write_json(destination.parent / 'provenance.json',
               {record['rendered_hash']: record for record in mapping})
    return manifest


def load_training_tokenizer(identifier: str, *, revision: str | None = None) -> ChatTokenizer:
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(identifier, revision=revision, local_files_only=True)
