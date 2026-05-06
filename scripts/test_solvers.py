import numpy as np

from lightaero.aerodynamics.solver import VLMDiscipline
from lightaero.geometry import build_ucrm_geometry
from lightaero.structures.solver import StructuralDiscipline

crm_geometry = build_ucrm_geometry()

M = 0.8
altitudes_m = np.arange(10000, 42001, 1000) * 0.3048
ALPHA = np.deg2rad(np.arange(-2.0, 4.0, 0.5))
for altitude_m in altitudes_m:
    vlm = VLMDiscipline()
    struct = StructuralDiscipline()
    for a in ALPHA:
        aero = vlm(
            wing=crm_geometry,
            alpha_rad=a,
            V_ms=200,
            altitude_m=altitude_m,
        )
        structure = struct(
            wing=crm_geometry,
            span_load=aero.span_load,
            span_drag=aero.span_drag,
            MTOW_kg=297_500.0,
            spar_thickness=np.full(crm_geometry.n_panels, 0.002),
        )
        print(
            f"{np.rad2deg(a):.2f}",
            f"{aero.CL:.4f}",
            f"{aero.CDi:.4f}",
            f"{aero.CM:.4f}",
            f"{structure.wing_mass_kg:.2f} kg",
            f"{structure.tip_deflection_m:.2f} m",
            f"{np.rad2deg(structure.tip_twist_rad):.2f} deg",
            sep=" | ",
        )
