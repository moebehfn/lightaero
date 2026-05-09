# Structural Theory

This page details the structural analysis methods and assumptions used in lightaero.

## Finite Element Model (FEM)

lightaero implements a 1D finite-element model of the wing spar based on Euler-Bernoulli beam theory.

### Euler-Bernoulli Beam

The model uses standard Hermite cubic shape functions for transverse displacement and slope.

#### Element Stiffness Matrix ($K_e$)

The $4 \times 4$ element stiffness matrix for a beam element with length $L$, Young's modulus $E$, and moment of inertia $I$ is:

$$
\mathbf{K}_e = \frac{EI}{L^3} \begin{bmatrix}
12 & 6L & -12 & 6L \\
6L & 4L^2 & -6L & 2L^2 \\
-12 & -6L & 12 & -6L \\
6L & 2L^2 & -6L & 4L^2
\end{bmatrix}
$$

#### Consistent Mass Matrix ($M_e$)

To account for inertial effects in dynamic analysis, a consistent mass matrix is derived using the same Hermite cubic shape functions as the stiffness matrix (Reddy, 1993):

$$
\mathbf{M}_e = \frac{\rho A L}{420} \begin{bmatrix}
156 & 22L & 54 & -13L \\
22L & 4L^2 & 13L & -3L^2 \\
54 & 13L & 156 & -22L \\
-13L & -3L^2 & -22L & 4L^2
\end{bmatrix}
$$

where $\rho$ is the material density and $A$ is the cross-sectional area.

!!! warning "Implementation Note: Static Analysis Only"
    Although the theoretical mass matrix formulas are provided above, the current structural discipline implementation in lightaero is limited to **static analysis**. Dynamic effects such as flutter, gust response, and modal analysis are not yet supported.

### Thin-Walled Section Properties

Wingbox section properties ($I_{xx}$, $I_{zz}$, $J$) are computed using numerical integration over a closed single-cell box outline (typically 15% to 65% chord).

#### Shear Center

The chordwise shear center position ($x_{sc}$) is determined via the Bredt-Batho method for a unit vertical shear.

#### Torsional Constant

The torsional constant ($J$) for the closed single-cell box is calculated as:

$$
J = \frac{4 A_e^2}{\oint \frac{1}{t} ds}
$$

where $A_e$ is the enclosed area and $t$ is the skin thickness.

## Stress Analysis

### Bending Stress

Bending stress is calculated from the vertical ($M_x$) and in-plane ($M_z$) bending moments:

$$
\sigma_{bending} = \frac{|M_x| y}{I_{xx}} + \frac{|M_z| x}{I_{zz}}
$$

### Torsional Shear Stress

Torsional shear stress ($\tau$) is computed using the Bredt-Batho formula for closed sections:

$$
\tau = \frac{T}{2 A_e t}
$$

where $T$ is the local torque.

### Von Mises Stress

The combined stress state is evaluated using the Von Mises criterion:
$$
\sigma_{vm} = \sqrt{\sigma_{bending}^2 + 3\tau^2}
$$

## Weight Estimation

### Structural Mass

Wing structural mass is obtained by spanwise integration of the material density ($\rho$) over the cross-sectional area ($A_{cross}$), adjusted by a structural factor ($k_{struct}$):

$$
m_{wing} = 2 \int_0^{b/2} \rho A_{cross} k_{struct} dy
$$

### Operating Empty Weight (OEW)

OEW is estimated using the Roskam log-linear regression for transport aircraft (Roskam, 1985):

$$
\log_{10}(OEW) = -0.0833 + 0.9647 \log_{10}(MTOW)
$$

## References

- Reddy, J. N. (1993). *An Introduction to the Finite Element Method* (2nd ed.). McGraw-Hill.
- Roskam, J. (1985). *Airplane Design Part V: Component Weight Estimation*. DARcorporation.
