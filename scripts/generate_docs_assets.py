import argparse
from pathlib import Path

from lightaero.geometry.ucrm import build_ucrm_geometry


def main():
    parser = argparse.ArgumentParser(description="Generate 3D wing visualization assets.")
    parser.add_argument("--output", default="docs/assets/fig.html", help="Output path")
    args = parser.parse_args()

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Use high-fidelity paneling for documentation as specified in Task 2
    wing = build_ucrm_geometry(n_panels=40)

    # Generate the visualization with specified parameters
    fig = wing.plot_wing_3d(
        show_panels=True,
        show_sections=False,
        show_grid=False,
        pov="top",
        save_dir=None,  # We will save it ourselves after manual updates
    )

    # Optimization for dark mode (per D-03)
    # Using plotly_dark template ensures text and grid are visible on dark themes
    # while maintaining transparency for seamless integration.
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    # Ensure scene background is also transparent
    fig.update_scenes(bgcolor="rgba(0,0,0,0)")

    # Save the final figure
    fig.write_html(str(out))

    print(f"Visualization generated at {out}")


if __name__ == "__main__":
    main()
