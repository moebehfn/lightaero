# Copyright 2026 lightaero
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Fidelity plugin registry for lightaero disciplines.

Provides a two-level namespace registry (family -> key -> class) so that
discipline implementations can be swapped by string key without modifying
coupling logic.

See: docs/theory/index.md
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable  # noqa: UP035

# ---------------------------------------------------------------------------
# Module-level singleton registry
# ---------------------------------------------------------------------------

#: Two-level namespace: DISCIPLINE_REGISTRY[family][key] = DisciplineClass
#: Populated by the @register decorator at import time.
DISCIPLINE_REGISTRY: dict[str, dict[str, type]] = {}


# ---------------------------------------------------------------------------
# Registration decorator
# ---------------------------------------------------------------------------


def register(family: str, key: str) -> Callable[[type], type]:
    """Decorator factory for two-level namespace registration.

    Registers the decorated class into `DISCIPLINE_REGISTRY[family][key]`.

    Args:
        family: Discipline family string (e.g. 'aero', 'structures').
        key: Fidelity/implementation key (e.g. 'vlm', 'low_fi').

    Returns:
        Callable[[type], type]: Decorator that registers the class and returns it unchanged.
    """

    def decorator(cls: type) -> type:
        if family not in DISCIPLINE_REGISTRY:
            DISCIPLINE_REGISTRY[family] = {}
        DISCIPLINE_REGISTRY[family][key] = cls
        return cls

    return decorator


# ---------------------------------------------------------------------------
# Registry lookup
# ---------------------------------------------------------------------------


def get_discipline(family: str, key: str) -> type:
    """Retrieve a discipline class from the registry.

    Args:
        family: Discipline family (e.g. 'aero').
        key: Implementation key (e.g. 'vlm').

    Returns:
        The registered class.

    Raises:
        KeyError: If family or key is not found.
    """
    if family not in DISCIPLINE_REGISTRY:
        available = list(DISCIPLINE_REGISTRY.keys())
        raise KeyError(
            f"Unknown discipline family: {family!r}. "
            f"Available families: {available}. "
            f"Ensure the discipline module has been imported."
        )
    if key not in DISCIPLINE_REGISTRY[family]:
        available = list(DISCIPLINE_REGISTRY[family].keys())
        raise KeyError(f"Unknown key {key!r} for family {family!r}. Available keys: {available}.")
    return DISCIPLINE_REGISTRY[family][key]


# ---------------------------------------------------------------------------
# DisciplineBase abstract class
# ---------------------------------------------------------------------------


class DisciplineBase(ABC):
    """Abstract base class for all lightaero discipline implementations.

    Enforces the black-box callable interface: discipline(inputs: dict) -> TypedDict

    See: docs/theory/index.md
    """

    @abstractmethod
    def __call__(self, **inputs: Any) -> Any:
        """Evaluate the discipline at the given inputs.

        Args:
            **inputs: Named physical quantities in SI units.

        Returns:
            Any: Results of the evaluation (e.g. AeroOutput, StructuralOutput).
        """
        ...
