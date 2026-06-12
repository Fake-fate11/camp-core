# V7 robust CAMP cross-version paired bootstrap

Positive route completion is better; negative red-light, jerk, lateral acceleration, fallback, and latency deltas are better.

| Comparison | Route completion | Planned red light | Mean jerk | Mean lateral acceleration |
| --- | ---: | ---: | ---: | ---: |
| v7 static - v5 static | -0.002670 [-0.010538, +0.002225] | -0.018194 [-0.046389, -0.002361] | -0.218978 [-0.465764, -0.014117] | +0.001025 [-0.010498, +0.016707] |
| v7 theta - v5 theta | -0.005587 [-0.014550, +0.000240] | -0.013472 [-0.029306, -0.002917] | +0.086273 [-0.184987, +0.452008] | -0.001554 [-0.007025, +0.003023] |
| v7 static - v6 static | -0.002649 [-0.010510, +0.002357] | -0.018194 [-0.045417, -0.002361] | -0.222170 [-0.467865, -0.015036] | +0.001445 [-0.010040, +0.017317] |
| v7 theta - v6 theta | -0.005324 [-0.014320, +0.000482] | -0.010972 [-0.027226, -0.000972] | +0.090217 [-0.200577, +0.451880] | +0.000871 [-0.004700, +0.005435] |

Each row contains 36 exactly matched route/seed/NPC/traffic-light pairs and 10,000 deterministic percentile-bootstrap resamples.
