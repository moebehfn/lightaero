# Aerodynamics Theory

## Vortex Lattice Method (VLM)

The Vortex Lattice Method (VLM) is a low-fidelity numerical method used to predict aerodynamic loads on lifting surfaces. It represents the wing as a collection of horseshoe vortex elements.

### Paneling

To resolve high-gradient regions at leading and trailing edges, the library uses cosine spacing for chordwise and spanwise distributions:

$$x_i = \frac{1}{2} [ 1 - \cos( \frac{i \cdot \pi}{N} ) ]$$

for $i = 0, \dots, N$. This distribution clusters panels near the boundaries where pressure gradients are steepest (Katz & Plotkin, 2001).

### Horseshoe Vortex Convention

Each panel $j$ has a horseshoe vortex consisting of:
- **Bound vortex segment**: $A_j \rightarrow B_j$ (inboard to outboard at quarter-chord)
- **Right trailing leg**: $B_j \rightarrow +\infty$ in freestream direction, strength $+\gamma$
- **Left trailing leg**: $A_j \rightarrow +\infty$ in freestream direction, strength $-\gamma$

### Biot-Savart Law

The velocity induced at a point $P$ by a vortex segment is given by the Biot-Savart law. For a finite segment $A \rightarrow B$:

$$ \mathbf{V} = \frac{\Gamma}{4\pi} \frac{\mathbf{r}_1 \times \mathbf{r}_2}{|\mathbf{r}_1 \times \mathbf{r}_2|^2} \left( \mathbf{r}_0 \cdot \left( \frac{\mathbf{r}_1}{|\mathbf{r}_1|} - \frac{\mathbf{r}_2}{|\mathbf{r}_2|} \right) \right) $$

where $\mathbf{r}_0 = \mathbf{B} - \mathbf{A}$, $\mathbf{r}_1 = \mathbf{P} - \mathbf{A}$, and $\mathbf{r}_2 = \mathbf{P} - \mathbf{B}$.

### Rankine Core Regularisation

To prevent singularities when a control point lies on or near a vortex axis, a Rankine core regularisation is used. The induced velocity denominator is bounded below:

$$ \text{denom} = \max(|\mathbf{r}_1 \times \mathbf{r}_2|^2, (\epsilon \cdot |\mathbf{r}_0|)^2) $$

where $\epsilon$ is a small fraction (typically $10^{-6}$).

### Aerodynamic Influence Coefficient (AIC) Matrix

The AIC matrix relates the circulation $\gamma_j$ of each panel to the normal velocity induced at control points $CP_i$:

$$ \mathbf{AIC} \cdot \mathbf{\gamma} = \mathbf{RHS} $$

The no-penetration boundary condition at each control point $i$ states:
$$ (\mathbf{V}_{\infty} + \mathbf{v}_{\text{induced}}) \cdot \hat{\mathbf{n}}_i = 0 $$
$$ \mathbf{RHS}_i = -(\mathbf{V}_{\infty} \cdot \hat{\mathbf{n}}_i) $$

## Static Aeroelasticity

The aeroelastic discipline couples the VLM aerodynamic solver with an Euler-Bernoulli structural beam model.

### Coupling Algorithm

1. Rebuild `WingGeometry` with current vertical deflection $z$ and elastic twist.
2. Run `VLMDiscipline` to obtain spanwise load and drag.
3. Run `StructuralDiscipline` to obtain spanwise deflection and twist.
4. Check convergence; if not converged (max change in deflection $> 0.01$ m), repeat.

The elastic twist (aeroelastic wash-out) captures the dominant load-relief mechanism on swept wings.

## Force Integration

### Near-Field Forces (Kutta-Joukowski)

Total forces are obtained by integrating the Kutta-Joukowski force on each bound vortex segment:

$$ \mathbf{F}_j = \rho \Gamma_j (\mathbf{V}_{\text{local},j} \times \mathbf{dl}_j) $$

Where $\mathbf{V}_{\text{local},j}$ is the local velocity vector at the midpoint of the bound segment, which includes the freestream velocity and the induced downwash from the entire vortex system (Katz & Plotkin, 2001).

### Trefftz-Plane Induced Drag

Induced drag is also computed in the Trefftz plane (far downstream) for better accuracy by evaluating the momentum deficit in the far-field:

$$ D_i = \frac{1}{2} \sum_{i=1}^{N} \Gamma_i \cdot w_{i, \infty} \cdot \Delta y_i $$

Note that the far-field normal wash $w_{i, \infty}$ is twice the bound-vortex downwash at the wing (Drela, 2014). For three-dimensional systems with non-planar wakes, the coefficient form is used:

$$ C_{Di} = -\frac{1}{V_{\infty}^2 S_{\text{ref}}} \sum \Gamma_j (w_{tp,j} \Delta y_j - v_{tp,j} \Delta z_j) $$

### Profile Drag

Zero-lift profile drag is estimated using turbulent flat-plate strip theory with a thickness form factor:
$$ C_{f} = \frac{0.074}{Re_c^{0.2}} $$
$$ FF = 1 + 2 \frac{t}{c} $$
$$ c_{d0} = 2 C_f FF $$

## References

- Katz, J. and Plotkin, A. "Low-Speed Aerodynamics", 2nd ed., Cambridge University Press, 2001.
- Drela, M. "Flight Vehicle Aerodynamics", MIT Press, 2014.
- Hodges, D.H. and Pierce, G.A., "Introduction to Structural Dynamics and Aeroelasticity", 2nd ed., Cambridge, 2011.
