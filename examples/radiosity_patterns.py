"""Solve selected illumination patterns without constructing a full matrix."""

import numpy as np

from lighttransport import groove_profile, solve_radiosity_patterns


profile = groove_profile(n_patches=48, angle_deg=70)
x = np.linspace(0.0, 1.0, 48)
patterns = np.stack([x, x[::-1]])
result = solve_radiosity_patterns(profile, patterns, albedo=0.7)
assert result.shape == patterns.shape
print(result[:, :4])
