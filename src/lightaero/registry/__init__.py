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

"""Fidelity plugin registry subpackage for lightaero.

Exposes DISCIPLINE_REGISTRY, register, get_discipline, and DisciplineBase
so that discipline modules can import from lightaero.registry directly:

    from lightaero.registry import register, DisciplineBase, DISCIPLINE_REGISTRY
"""

from lightaero.registry.registry import (
    DISCIPLINE_REGISTRY,
    DisciplineBase,
    get_discipline,
    register,
)

__all__ = [
    "DISCIPLINE_REGISTRY",
    "register",
    "get_discipline",
    "DisciplineBase",
]
