from typing import Protocol

from cybersos.simulator import Observation


class Policy(Protocol):
    def __call__(self, observation: Observation) -> str: ...
