from pathlib import Path

from lightaero.geometry.ucrm import build_ucrm_geometry

wing = build_ucrm_geometry(n_panels=40)
wing.plot_wing_3d(
    show_panels=False,
    show_sections=False,
    show_grid=False,
    # pov="top",
    save_dir=Path(__file__).parent / "fig.html",
)
