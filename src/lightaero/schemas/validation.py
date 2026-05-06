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

"""Runtime validator for discipline output dicts.

See: docs/theory/index.md
"""

from __future__ import annotations

import logging
import math
import warnings
from dataclasses import fields
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def check_regime_validity(mach: float, aoa_rad: float) -> None:
    """Check if flight condition is within standard VLM validity bounds.

    Issues UserWarning if:
    - Mach > 0.3 (incompressible limit)
    - |AoA| > 10 degrees (linear lift limit)

    Args:
        mach: Mach number.
        aoa_rad: Angle of attack in radians.
    """
    if mach > 0.3:
        msg = f"Mach {mach:.2f} exceeds incompressible limit (0.3). Results may be inaccurate."
        warnings.warn(msg, UserWarning, stacklevel=2)
        logger.warning(msg)

    aoa_deg = math.degrees(aoa_rad)
    if abs(aoa_deg) > 10.0:
        msg = f"AoA {aoa_deg:.1f} deg exceeds typical VLM linear limit (10 deg). Results may be inaccurate."
        warnings.warn(msg, UserWarning, stacklevel=2)
        logger.warning(msg)


def validate_discipline_output(output: Any, spec: dict) -> None:
    """Runtime validation of a discipline output dict against a spec.

    Checks key presence, type correctness, array shape, and plausibility bounds.

    Args:
        output: Object (dataclass) returned by a discipline's __call__ method.
        spec: Companion spec dict (e.g. AERO_OUTPUT_SPEC).

    Raises:
        ValueError: Missing required key, wrong array shape, or out-of-bounds value.
        TypeError: Wrong Python type for a field.
    """
    # --- 1. Key presence ---
    missing = set(spec.keys()) - set([f.name for f in fields(output)])
    if missing:
        # Report all missing keys in alphabetical order for deterministic messages
        missing_str = ", ".join(sorted(missing))
        raise ValueError(f"Missing required output keys: {missing_str}")

    # --- 2. Type, shape, and bounds per field ---
    for key, rules in spec.items():
        val: Any = getattr(output, key)
        expected_type = rules["type"]

        # Type check - use isinstance
        if not isinstance(val, expected_type):
            raise TypeError(f"Output field '{key}': expected {expected_type.__name__}, got {type(val).__name__}")

        # Array shape check (applies only when type is np.ndarray)
        if expected_type is np.ndarray and "shape_dim" in rules:
            expected_ndim: int = rules["shape_dim"]
            if val.ndim != expected_ndim:
                raise ValueError(
                    f"Output field '{key}': expected {expected_ndim}D array, "
                    f"got {val.ndim}D array with shape {val.shape}"
                )

        # Plausibility bounds check (applies only to scalar types with bounds)
        if "bounds" in rules and expected_type is not np.ndarray:
            lo, hi = rules["bounds"]
            scalar_val = float(val)
            if lo is not None and scalar_val < lo:
                raise ValueError(
                    f"Output field '{key}' = {scalar_val} is below minimum "
                    f"plausible value {lo}. Check SI units (possible unit mismatch)."
                )
            if hi is not None and scalar_val > hi:
                raise ValueError(
                    f"Output field '{key}' = {scalar_val} is above maximum "
                    f"plausible value {hi}. Check SI units (possible unit mismatch)."
                )

    return None
