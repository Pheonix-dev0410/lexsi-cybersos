from collections.abc import Iterable, Mapping


def render_rule_lines(rules: Iterable[Mapping[str, object]]) -> list[str]:
    """Retrieved rules as `steps: required facts [sources]`, in retrieval order.

    Requirements shared by every retrieved step are stated once, and steps with identical
    prerequisites and sources share one line. URLs, review metadata and user-facing
    instructions are omitted: the application supplies them, and the policy only needs step
    ids, prerequisites and the source ids that `finish` cites.
    """
    rules = list(rules)
    requirements = [{f'{field}={value}' for field, value in rule['requires'].items()}  # type: ignore[union-attr]
                    for rule in rules]
    shared = set.intersection(*requirements) if len(rules) > 1 else set()
    groups: dict[tuple[str, str], list[str]] = {}
    for rule, required in zip(rules, requirements):
        condition = ', '.join(sorted(required - shared)) or 'nothing further'
        if rule.get('unknown_requires_question') is False:
            condition += '; unknown facts need no question'
        sources = ', '.join(rule.get('source_ids', ()))  # type: ignore[arg-type]
        groups.setdefault((condition, sources), []).append(str(rule['step_id']))
    lines = [f'Every retrieved step requires {", ".join(sorted(shared))}.'] if shared else []
    return lines + [f'{", ".join(steps)}: {condition} [{sources}]'
                    for (condition, sources), steps in groups.items()]
