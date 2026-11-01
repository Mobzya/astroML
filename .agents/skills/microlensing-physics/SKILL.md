---
name: microlensing-physics
description: Validate and implement point-source point-lens microlensing physics, photometry, lightcurve simulators, parameter fitting and physical plausibility for the AstroML competition research project.
---

Use for tasks involving equations, flux, noise, PSPL simulations, validation of astronomical claims and parameter retrieval.

1. Work in flux units and document normalization; do not interchange magnitudes with flux.
2. Use u(t)=sqrt(u0²+((t-t0)/tE)²), A(u)=(u²+2)/(u sqrt(u²+4)); F=Fs*A+Fb+noise. Valid u0>0 and tE>0. Handle numerical limits at small u.
3. Unit tests: A(u)>1 for finite u>0; approaches 1 as u grows; symmetry of ideal A(t) around t0; smaller u0 gives higher peak; extending tE makes event broader; F asymptotes to Fs+Fb.
4. Simulate realistic irregular times, weather/season gaps, heteroskedastic sigma and missing peak. Explicitly document assumptions. Check noise realizations across seeds.
5. Fit with correct weights sigma_i, bounds and multiple initializations, check degeneracies; report uncertainty and failure modes.
6. Validate against a reputable independently implemented library where feasible, e.g., MulensModel; if unavailable, document blocked verification.
7. Never infer black-hole identity or lens mass from an isolated PSPL photometric event; tE combines mass, geometry and relative proper motion.
8. Whenever method assumptions fail (binary lens, blending variations, parallax, finite-source), state scope and stop overinterpretation.
9. Outputs: tests, derivation notes, physically labelled plots, source bibliography and clear unit/parameter descriptions.
