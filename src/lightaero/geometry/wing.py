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

"""Parametric wing geometry.

See: docs/theory/index.md for parametric wing construction and cosine spacing details.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from lightaero.geometry.airfoil import blended_profile, interpolate_camber


def _cosine_y_cp(half_span: float, n_panels: int) -> np.ndarray:
    """Cosine-spaced control-point y coordinates (one semi-span)."""
    theta = np.linspace(0.0, np.pi, n_panels + 1)
    y_nodes = (half_span / 2.0) * (1.0 - np.cos(theta))
    y_cp = 0.5 * (y_nodes[:-1] + y_nodes[1:])
    return y_cp


def _cosine_y_nodes(half_span: float, n_panels: int) -> np.ndarray:
    """Cosine-spaced node y-coordinates, shape (n_panels+1,)."""
    theta = np.linspace(0.0, np.pi / 2.0, n_panels + 1)
    return half_span * np.sin(theta)


@dataclass(frozen=True)
class WingGeometry:
    """Parametric wing geometry with cosine-spaced panel arrays.

    See: docs/theory/index.md for detailed field descriptions and mathematical foundations.

    Attributes:
        half_span: Semi-span in metres.
        n_panels: Number of spanwise panels.
        y_stations: Spanwise break positions.
        chord: Chord lengths at each station.
        sweep_le: Leading-edge sweep angles (rad).
        taper: Local taper ratios.
        twist: Geometric twist angles (rad).
        airfoil_sections: Tuple of AirfoilSection objects.
        deflection_z: Transverse nodal displacements (m).
    """

    # --- Planform inputs ---
    half_span: float
    n_panels: int
    y_stations: np.ndarray
    chord: np.ndarray
    sweep_le: np.ndarray
    taper: np.ndarray
    twist: np.ndarray
    airfoil_sections: tuple
    deflection_z: np.ndarray = None

    # --- Derived arrays ---
    y_cp: np.ndarray = field(init=False)
    chord_cp: np.ndarray = field(init=False)
    camber_cp: np.ndarray = field(init=False)
    twist_cp: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        """Compute derived arrays and lock all arrays as read-only."""
        y_cp = _cosine_y_cp(self.half_span, self.n_panels)

        if self.deflection_z is None:
            deflection_z = np.zeros(self.n_panels + 1)
        else:
            deflection_z = np.asarray(self.deflection_z, dtype=float)
            if deflection_z.shape != (self.n_panels + 1,):
                raise ValueError(f"deflection_z must have shape ({self.n_panels + 1},), got {deflection_z.shape}")

        chord_cp = np.interp(y_cp, self.y_stations, self.chord)
        twist_cp = np.interp(y_cp, self.y_stations, self.twist)

        x_mid = np.array([0.5])
        camber_cp = np.array(
            [
                float(
                    interpolate_camber(
                        y,
                        self.y_stations,
                        list(self.airfoil_sections),
                        x_mid,
                    )[0]
                )
                for y in y_cp
            ]
        )

        for arr_name, arr in [
            ("y_stations", self.y_stations),
            ("chord", self.chord),
            ("sweep_le", self.sweep_le),
            ("taper", self.taper),
            ("twist", self.twist),
        ]:
            arr_ro = np.array(arr)
            arr_ro.flags.writeable = False
            object.__setattr__(self, arr_name, arr_ro)

        for arr_name, arr in [
            ("y_cp", y_cp),
            ("chord_cp", chord_cp),
            ("twist_cp", twist_cp),
            ("camber_cp", camber_cp),
            ("deflection_z", deflection_z),
        ]:
            arr.flags.writeable = False
            object.__setattr__(self, arr_name, arr)

    def _section_at_y(self, y: float, n_profile_points: int) -> dict:
        """Compute scaled, swept, twisted airfoil profile at position y."""
        y_nodes = _cosine_y_nodes(self.half_span, self.n_panels)
        deflection = float(np.interp(y, y_nodes, self.deflection_z))

        x_norm, z_norm = blended_profile(y, self.y_stations, list(self.airfoil_sections), n_profile_points)
        c = float(np.interp(y, self.y_stations, self.chord))
        theta = float(np.interp(y, self.y_stations, self.twist))
        sweep = float(np.interp(y, self.y_stations, self.sweep_le))

        x_scaled = x_norm * c
        z_scaled = z_norm * c

        cos_t, sin_t = np.cos(theta), np.sin(theta)
        x_rot = cos_t * x_scaled + sin_t * z_scaled
        z_rot = -sin_t * x_scaled + cos_t * z_scaled

        x_rot = x_rot + y * np.tan(sweep)
        z_rot = z_rot + deflection

        return {"y": float(y), "x": x_rot, "z": z_rot}

    def get_wing_coordinates(self, n_profile_points: int = 50) -> list[dict]:
        """Return scaled and twisted airfoil coordinates at each control point."""
        return [self._section_at_y(float(y), n_profile_points) for y in self.y_cp]

    def plot_wing_3d(
        self,
        n_profile_points: int = 50,
        alpha_deg: float = 0.0,
        colorscale: str = "Blues",
        show_sections: bool = True,
        show_panels: bool = False,
        save_dir: str | None = None,
        show_grid=False,
        pov: str | None = None,
    ):
        """Render a 3D visualization of the wing using Plotly."""
        import plotly.graph_objects as go

        _POV = {
            "top": dict(eye=dict(x=0, y=0, z=+1), up=dict(x=-1, y=0, z=0)),
            "bottom": dict(eye=dict(x=0, y=0, z=-1), up=dict(x=-1, y=0, z=0)),
            "front": dict(eye=dict(x=-1, y=0, z=0), up=dict(x=0, y=0, z=1)),
            "rear": dict(eye=dict(x=+1.35, y=0, z=0), up=dict(x=0, y=0, z=1)),
            "left": dict(eye=dict(x=0, y=-1, z=0), up=dict(x=0, y=0, z=1)),
            "right": dict(eye=dict(x=0, y=+1, z=0), up=dict(x=0, y=0, z=1)),
            "iso": dict(eye=dict(x=1.5, y=-1.5, z=0.75), up=dict(x=0, y=0, z=1)),
        }
        if pov is not None and pov not in _POV:
            raise ValueError(f"pov must be one of {list(_POV)} or None, got {pov!r}")

        def mirror(sections):
            return [{"y": -s["y"], "x": s["x"], "z": s["z"]} for s in reversed(sections)]

        cp_sections = self.get_wing_coordinates(n_profile_points)
        all_cp = mirror(cp_sections) + cp_sections

        y_nodes = _cosine_y_nodes(self.half_span, self.n_panels)
        node_sections = [self._section_at_y(float(y), n_profile_points) for y in y_nodes]
        all_nodes = mirror(node_sections) + node_sections

        n_pts = 2 * n_profile_points
        n_sec = len(all_nodes)
        X = np.empty((n_pts, n_sec))
        Y = np.empty((n_pts, n_sec))
        Z = np.empty((n_pts, n_sec))
        for j, sec in enumerate(all_nodes):
            if alpha_deg != 0.0:
                from scipy.spatial.transform import Rotation as R

                r = R.from_euler("y", alpha_deg, degrees=True)
                sec["x"], sec["y"], sec["z"] = r.apply(np.matrix([sec["x"], [sec["y"]] * len(sec["x"]), sec["z"]]).T).T

            X[:, j] = sec["x"]
            Y[:, j] = sec["y"]
            Z[:, j] = sec["z"]

        traces = [
            go.Surface(
                x=X,
                y=Y,
                z=Z,
                colorscale=colorscale,
                showscale=False,
                lighting=dict(ambient=0.5, diffuse=0.8, specular=0.2),
                opacity=1.0,
            )
        ]

        if show_sections:
            for sec in all_cp:
                x_closed = np.append(sec["x"], sec["x"][0])
                z_closed = np.append(sec["z"], sec["z"][0])
                traces.append(
                    go.Scatter3d(
                        x=x_closed,
                        y=np.full_like(x_closed, sec["y"]),
                        z=z_closed,
                        mode="lines",
                        line=dict(color="royalblue", width=2),
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )

        if show_panels:
            for sec in all_nodes:
                x_closed = np.append(sec["x"], sec["x"][0])
                z_closed = np.append(sec["z"], sec["z"][0])
                traces.append(
                    go.Scatter3d(
                        x=x_closed,
                        y=np.full_like(x_closed, sec["y"]),
                        z=z_closed,
                        mode="lines",
                        line=dict(color="crimson", width=1),
                        showlegend=False,
                        hoverinfo="skip",
                    )
                )

        all_x, all_y, all_z = X.ravel(), Y.ravel(), Z.ravel()
        max_range = max(all_x.max() - all_x.min(), all_y.max() - all_y.min(), all_z.max() - all_z.min())
        cx, cy, cz = (
            0.5 * (all_x.max() + all_x.min()),
            0.5 * (all_y.max() + all_y.min()),
            0.5 * (all_z.max() + all_z.min()),
        )
        half = 0.5 * max_range

        camera = _POV[pov] if pov is not None else None
        dragmode = False if pov is not None else "orbit"

        scene = dict(
            xaxis=dict(
                title="x (m)" if show_grid else "",
                range=[cx - half, cx + half],
                showbackground=False,
                showgrid=show_grid,
                showticklabels=show_grid,
                gridcolor="grey",
            ),
            yaxis=dict(
                title="y (m)" if show_grid else "",
                range=[cy - half, cy + half],
                showbackground=False,
                showgrid=show_grid,
                showticklabels=show_grid,
                gridcolor="grey",
            ),
            zaxis=dict(
                title="z (m)" if show_grid else "",
                range=[cz - half, cz + half],
                showbackground=False,
                showgrid=show_grid,
                showticklabels=show_grid,
                gridcolor="grey",
            ),
            aspectmode="cube",
            bgcolor="rgba(0,0,0,0)",
        )
        if camera is not None:
            scene["camera"] = camera

        fig = go.Figure(data=traces)
        fig.update_layout(
            scene=scene,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            dragmode=dragmode,
        )

        if save_dir:
            fig.write_html(save_dir)

        return fig


def build_wing_geometry(
    half_span: float,
    n_panels: int,
    y_stations: np.ndarray,
    chord: np.ndarray,
    sweep_le: np.ndarray,
    taper: np.ndarray,
    twist: np.ndarray,
    airfoil_sections: tuple,
    deflection_z: np.ndarray = None,
) -> WingGeometry:
    """Factory for WingGeometry with input validation.

    See: docs/theory/index.md for geometric constraints and validation rules.
    """
    y_stations = np.asarray(y_stations, dtype=float)
    chord = np.asarray(chord, dtype=float)
    sweep_le = np.asarray(sweep_le, dtype=float)
    taper = np.asarray(taper, dtype=float)
    twist = np.asarray(twist, dtype=float)

    if half_span <= 0.0:
        raise ValueError(f"half_span must be positive, got {half_span}")
    if n_panels < 4:
        raise ValueError(f"n_panels must be >= 4, got {n_panels}")
    n_sections = len(y_stations)
    if n_sections < 2:
        raise ValueError("y_stations must have at least 2 entries (root and tip)")
    if not np.isclose(y_stations[0], 0.0):
        raise ValueError(f"y_stations[0] must be 0.0 (root), got {y_stations[0]}")
    if not np.isclose(y_stations[-1], half_span):
        raise ValueError(f"y_stations[-1] must equal half_span={half_span}, got {y_stations[-1]}")
    if not np.all(np.diff(y_stations) > 0):
        raise ValueError("y_stations must be strictly monotonically increasing")
    for arr_name, arr in [("chord", chord), ("sweep_le", sweep_le), ("taper", taper), ("twist", twist)]:
        if arr.shape != (n_sections,):
            raise ValueError(f"{arr_name} must have shape ({n_sections},), got {arr.shape}")
    if np.any(chord <= 0.0):
        raise ValueError("All chord values must be positive")
    if len(airfoil_sections) != n_sections:
        raise ValueError(f"airfoil_sections must have {n_sections} entries, got {len(airfoil_sections)}")

    return WingGeometry(
        half_span=float(half_span),
        n_panels=int(n_panels),
        y_stations=y_stations,
        chord=chord,
        sweep_le=sweep_le,
        taper=taper,
        twist=twist,
        airfoil_sections=tuple(airfoil_sections),
        deflection_z=deflection_z,
    )
