# gas-grid-ogd-gurobi
Study project for Optimal Gas Dispatch with Gurobi.

Repository layout:
- `src/common/` for shared loading, validation, outputs, and run orchestration
- `src/weymouth_ogd/` for the full nonlinear bidirectional formulation
- `src/weymouth_lp_ogd/` for the mono-direction piecewise linear formulation

Current formulations:
- `weymouth_ogd`: quadratic Weymouth formulation for Gurobi MIQCP
- `weymouth_lp_ogd`: linear Weymouth approximation using tangent planes and 5 pressure intervals

The code stays close to the legacy style:
- simple class-based model assembly
- canonical loader with aliases for old CSV headers
- small case studies first, then larger networks
- output artifacts written under `outputs/<case>/<formulation>/latest/`

Run examples:

```bash
conda run -n gurobi python main.py --case custom_MP_4nodes --formulation weymouth_ogd --load-factor 0.49
conda run -n gurobi python main.py --case custom_MP_4nodes --formulation weymouth_lp_ogd --load-factor 0.49
conda run -n gurobi python main.py --case ringed_MP_7nodes --formulation weymouth_ogd
conda run -n gurobi python main.py --case ringed_LP_7nodes --formulation weymouth_lp_ogd
conda run -n gurobi python main.py --case ZUG_1300nodes --formulation weymouth_ogd --load-factor 0.05
```

The small custom case needs a slightly reduced load factor to be fully served with the legacy pipe data. The ringed cases solve at full load once the valve link is included.

Plots:
- OpenStreetMap is used when geographic coordinates can be interpreted
- otherwise the network is drawn on a blank background
- each run writes a network plot and a pressure heatmap
