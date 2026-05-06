# Assumptions & Limitations

This page documents the physical and numerical boundaries of the lightaero library. As a low-fidelity tool intended for preliminary research, the library makes several standard simplifications that limit its applicability to specific flight regimes.

## Major Physical Assumptions

### Aerodynamics
lightaero's primary aerodynamic solver is based on the **Vortex Lattice Method (VLM)**.

- **Inviscid Flow**: The fluid is assumed to be inviscid (no boundary layers, no separation). While profile drag is estimated using empirical form factors, it does not capture separation-induced drag.
- **Incompressible Flow**: The standard VLM implementation assumes the fluid is incompressible. Compressibility effects (Prandtl-Glauert) are currently not implemented.
- **Small Perturbations**: The theory assumes small angles of attack and small perturbations to the freestream.
- **Potential Flow**: Flow is assumed to be irrotational, except on the vortex filaments themselves.

!!! warning "Validity Regime: Mach Number"
    Standard VLM is strictly valid for incompressible flow (Mach < 0.3). While calculations may run at higher speeds, results will be physically inaccurate as compressibility effects are ignored [Katz & Plotkin, 2001].

!!! warning "Validity Regime: Angle of Attack"
    VLM predicts linear lift growth even at very high AoA. In reality, wings stall. Results for $\alpha > 10^\circ$ should be treated with extreme caution as viscous separation and stall are not modeled.

### Structures
- **Linear Elasticity**: The structural model assumes materials remain in the linear elastic regime.
- **Euler-Bernoulli Beam Theory**: Wings are modeled as 1D beams. Shear deformation and large deflections are not accounted for.
- **Static Analysis**: The current implementation is limited to static aeroelastic analysis.

### Atmosphere
- **International Standard Atmosphere (ISA)**: Calculations use the ISA model (ISO 2533 / ICAO) for density and pressure.

## Implementation Discrepancies

### Altitude Calculation
!!! warning "Geometric vs. Geopotential Altitude"
    The current atmosphere implementation uses **geometric altitude** ($z$) as the input for density calculations, whereas the ISA standard is defined in terms of **geopotential altitude** ($H$).
    At 10,000 m, the error is approximately 16m (0.16%), which is generally considered acceptable for low-fidelity research but should be noted for high-precision comparisons.

### Structural Dynamics
!!! warning "Static Analysis Only"
    Although the theoretical documentation provides formulas for mass matrices, the current structural discipline is limited to **static analysis**. Dynamic effects (flutter, gust response) are not yet implemented.

## References

- Katz, J. and Plotkin, A. *Low-Speed Aerodynamics*, 2nd ed., Cambridge University Press, 2001.
- Drela, M. *Flight Vehicle Aerodynamics*, MIT Press, 2014.
- ISO 2533:1975, *Standard Atmosphere*.
