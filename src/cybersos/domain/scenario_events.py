from dataclasses import dataclass

from cybersos.domain.access import AccessField, FactValue, normalize_value
from cybersos.domain.actions import ToolName


@dataclass(frozen=True)
class UserCorrection:
    field: AccessField
    value: FactValue
    after_question: AccessField | None = None
    after_step_id: str | None = None
    message: str = ''

    def __post_init__(self) -> None:
        object.__setattr__(self, 'field', AccessField(self.field))
        object.__setattr__(self, 'value', normalize_value(self.field, self.value))
        if (self.after_question is None) == (self.after_step_id is None):
            raise ValueError('A correction needs exactly one semantic trigger')
        if self.after_question is not None:
            object.__setattr__(self, 'after_question', AccessField(self.after_question))
        if self.after_step_id is not None and (
                not isinstance(self.after_step_id, str) or not self.after_step_id):
            raise ValueError('A step trigger needs a nonempty step ID')
        if not isinstance(self.message, str):
            raise ValueError('Correction message must be text')


@dataclass(frozen=True)
class TemporaryToolFailure:
    tool_name: ToolName
    step_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, 'tool_name', ToolName(self.tool_name))
        if self.step_id is not None and (
                self.tool_name not in {ToolName.CHECK_STEP, ToolName.SIMULATE_STEP} or
                not isinstance(self.step_id, str) or not self.step_id):
            raise ValueError('Only step tools accept a nonempty step ID')
