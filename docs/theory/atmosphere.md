# Atmosphere Theory

## International Standard Atmosphere (ISA)

The International Standard Atmosphere (ISA) is a static atmospheric model of how the pressure, temperature, density, and viscosity of the Earth's atmosphere change over a wide range of altitudes or elevations.

### Altitude Conversion

Atmospheric properties are calculated based on geopotential altitude $H$, which accounts for the variation of gravity with height. The relationship between geopotential altitude $H$ and geometric height $Z$ is:

$$ H = \frac{R_e \cdot Z}{R_e + Z} $$

where $R_e \approx 6,356,766$ m is the effective radius of the Earth for atmospheric calculations (ISO 2533:1975).

!!! warning "Implementation Note: Geometric vs. Geopotential Altitude"
    While the ISA model is formally defined in terms of geopotential altitude ($H$), the current lightaero implementation uses **geometric altitude** ($Z$) as the direct input for all atmospheric property calculations. 
    
    This simplification avoids the conversion step but introduces a small error that increases with altitude (approximately 0.16% at 10,000 m). For most preliminary research applications, this error is considered negligible.

### Layers

The model covers two layers:
1. **Troposphere** (0 to 11,000 m): Linear temperature lapse rate.
2. **Tropopause** (11,000 to 20,000 m): Constant temperature (isothermal).

### Governing Equations

#### Troposphere ($h < 11,000$ m)

$$ T = T_0 - L h $$
$$ p = p_0 \left( \frac{T}{T_0} \right)^{\frac{g_0}{R L}} $$
$$ \rho = \frac{p}{R T} $$

#### Tropopause ($h \ge 11,000$ m)

$$ T = T_{tp} $$
$$ p = p_{tp} \exp\left( -\frac{g_0 (h - H_{tp})}{R T_{tp}} \right) $$
$$ \rho = \frac{p}{R T_{tp}} $$

### Dynamic Viscosity

The dynamic viscosity $\mu$ is calculated using Sutherland's Law, which accounts for the effect of temperature on the viscosity of a gas:

$$ \mu = \mu_0 \frac{T_0 + S}{T + S} \left( \frac{T}{T_0} \right)^{3/2} $$

For air, the standard constants (ICAO Doc 7488) are:
- $\mu_0 = 1.716 \times 10^{-5}$ Pa·s
- $T_0 = 273.15$ K
- $S = 110.4$ K

### Speed of Sound

The speed of sound $a$ in the atmosphere is a function of the local air temperature:

$$ a = \sqrt{\gamma R T} $$

where $\gamma = 1.4$ is the ratio of specific heats for air.

### Constants

- $T_0 = 288.15$ K
- $p_0 = 101325.0$ Pa
- $R = 287.05287$ J/(kg·K)
- $g_0 = 9.80665$ m/s$^2$
- $L = 0.0065$ K/m

### References

- ISO 2533:1975, "Standard Atmosphere", International Organization for Standardization.
- ICAO Doc 7488/3, "Manual of the ICAO Standard Atmosphere", 3rd Edition, 1993, International Civil Aviation Organization.
