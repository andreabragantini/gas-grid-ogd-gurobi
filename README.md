# Gas Grid OGD Gurobi

A modular Python framework for optimizing gas network dispatch using Gurobi solver. This study project rebuilds legacy code into a maintainable architecture suitable for research and portfolio presentation.

**Key features:**
- Multiple solution formulations: quadratic (Weymouth MIQCP) and piecewise-linear approximations
- Automatic data harmonization across different case formats (alias-based schema)
- Full end-to-end pipeline: data loading → optimization → report generation → visualization
- Test suite for data validation and solution verification
- Batch runner for executing multiple scenarios

---

## Quick Start

### Prerequisites

- Python 3.9+
- Gurobi 10.0+ (with license)
- Conda environment with `gurobi` installed

### Installation

```bash
# Clone and navigate to repository
cd gas-grid-ogd-gurobi

# Verify environment
python -m pytest tests/ -v
```

---

## Usage

### Basic: Single Run

Run the default case (4-node) with full demand:

```bash
python main.py
```

Run a specific case with a custom formulation:

```bash
python main.py --case ringed_LP_7nodes --formulation weymouth_lp_ogd
```

Run with reduced load factor (70% of nominal demand):

```bash
python main.py --case custom_MP_4nodes --formulation weymouth_ogd --load-factor 0.7
```

### View Available Cases

```bash
python main.py --list-cases
```

Output shows directory names in `data/`:
```
custom_MP_4nodes
ringed_LP_7nodes
ringed_MP_7nodes
ZUG_1300nodes
```

### Batch: Run Multiple Cases

Run all cases with both formulations:

```bash
python batch_runner.py
```

Run specific cases only:

```bash
python batch_runner.py --cases custom_MP_4nodes ringed_LP_7nodes
```

Run only the linear formulation at reduced load:

```bash
python batch_runner.py --formulations weymouth_lp_ogd --load-factor 0.5
```

List predefined batch scenarios:

```bash
python batch_runner.py --list-scenarios
```

### Understanding the Output

All results are written to: `outputs/<case_name>/<formulation_name>/latest/`

Structure:
```
outputs/custom_MP_4nodes/weymouth_ogd/latest/
├── index.html                # Interactive report
├── kpi_snapshot.json         # Key performance indicators (JSON)
├── run_metadata.json         # Run parameters and timestamps
├── tables/
│   ├── node_pressure.csv     # Node pressures (solution)
│   ├── pipe_flow.csv         # Pipe flows
│   ├── direction.csv         # Flow directions
│   ├── active_supply.csv     # Supplier dispatch
│   └── ...                   # Additional solution tables
└── charts/
    ├── network.html          # Network topology visualization
    ├── pressure_heatmap.html # Pressure profile heatmap
    └── ...                   # Additional charts
```

**Console Output Example:**

```
======================================================================
  Gas Network Optimization Run
======================================================================

Start time:     2026-06-02 14:23:45
Case:           custom_MP_4nodes
Formulation:    weymouth_ogd
Load factor:    49.0%

======================================================================
  Run Completed Successfully
======================================================================

Status:         OPTIMAL
Output:         outputs/custom_MP_4nodes/weymouth_ogd/latest
Index HTML:     outputs/custom_MP_4nodes/weymouth_ogd/latest/index.html
KPI Summary:    outputs/custom_MP_4nodes/weymouth_ogd/latest/kpi_snapshot.json
Tables:         outputs/custom_MP_4nodes/weymouth_ogd/latest/tables/
Charts:         outputs/custom_MP_4nodes/weymouth_ogd/latest/charts/
Metadata:       outputs/custom_MP_4nodes/weymouth_ogd/latest/run_metadata.json
```

---

## Testing

Run individual test modules to verify the pipeline:

```bash
# Data loading and schema harmonization tests
python -m unittest tests/test_loader.py -v

# End-to-end smoke test
python -m unittest tests/test_smoke_solve.py -v
```

### What Tests Verify

- **test_loader.py**: 
  - Schema alias resolution (different column names → canonical)
  - Unit normalization (m/km, mm, Pa/bar → kPa)
  - Reference integrity (pipes don't reference undefined nodes)
  - Optional file handling

- **test_smoke_solve.py**:
  - Small case solves to optimality
  - All output directories and files are created
  - HTML report, KPI JSON, and solution tables exist

---

## Formulations

### `weymouth_ogd` (Quadratic, MIQCP)

Full nonlinear bidirectional Weymouth formulation for Gurobi MIQCP model:

- **Variables**: Node pressures, pipe flows (bidirectional), source dispatch, flow direction binary indicators
- **Physics**: Weymouth pressure-flow relationship
- **Problem type**: Mixed-integer quadratically-constrained program
- **Typical use**: Smaller networks, high accuracy needed
- **Recommended**: custom_MP_4nodes, ringed_MP_7nodes

### `weymouth_lp_ogd` (Piecewise-Linear, LP)

Linear approximation of Weymouth using tangent planes over 5 pressure intervals:

- **Variables**: Node pressures, pipe flows (one direction), source dispatch, flow interval binary
- **Physics**: Linearized via tangent-plane approximation
- **Problem type**: Mixed-integer linear program
- **Typical use**: Larger networks, faster solve
- **Recommended**: ringed_LP_7nodes, ZUG_1300nodes (if it fits in memory)

---

## Architecture

### Project Structure

```
src/
├── common/                  # Shared components
│   ├── context.py          # RunConfig, GasNetworkData dataclasses
│   ├── loader.py           # Data loading with alias resolution
│   ├── schema.py           # Column aliases and unit converters
│   ├── validation.py       # Reference and bounds checking
│   ├── runner.py           # Orchestration: load → solve → output
│   └── outputs.py          # Artifact writing (HTML, JSON, CSV)
│
├── weymouth_ogd/           # Quadratic formulation
│   ├── variables.py        # Decision variables
│   ├── constraints.py      # Model constraints
│   ├── objective.py        # Objective function
│   ├── model.py            # Gurobi model builder
│   ├── results.py          # Solution extraction
│   └── chart.py            # Visualization
│
└── weymouth_lp_ogd/        # Linear approximation
    ├── variables.py
    ├── constraints.py
    ├── objective.py
    ├── model.py
    ├── results.py
    └── chart.py
```

### Data Flow

```
main.py or batch_runner.py
    ↓
data/ → load_case (loader.py)
    ↓
GasNetworkData (validated)
    ↓
formulation_registry.create_formulation() → Formulation class
    ↓
formulation.solve(data) → Gurobi model
    ↓
FormulationRun (status, tables, KPIs, charts)
    ↓
OutputManager.write() → outputs/ directory
    ↓
RunOutcome (with artifact paths)
```

---

## Case Studies

### small: custom_MP_4nodes
- **Nodes**: 4  
- **Pipes**: 3  
- **Notes**: Baseline test case; requires `--load-factor 0.49` for full feasibility
- **Typical solve time**: < 1 second

### Small: ringed_LP_7nodes / ringed_MP_7nodes
- **Nodes**: 7 (with loop)
- **Pipes**: 8 + valve  
- **Notes**: Includes manual valve link; solves at full load
- **Typical solve time**: < 2 seconds

### Large: ZUG_1300nodes
- **Nodes**: ~1,300  
- **Pipes**: ~1,900  
- **Notes**: Production dataset; memory-intensive; use `weymouth_lp_ogd` + reduced load
- **Typical solve time**: 10-60 seconds (depending on formulation)

---

## Data Format

Each case directory in `data/` should contain:

**Required files:**
- `gas_nodes.csv` – Node definitions (ID, pressure bounds, demand, coordinates)
- `gas_pipes.csv` – Pipe definitions (ID, from/to nodes, length, diameter, friction)
- `gas_reservoir.csv` – Supply nodes (ID, node reference, capacity, cost)

**Optional files:**
- `gas_loads_special.csv` – Additional load points
- `gas_valves.csv` – Valve definitions (for flow restriction)
- `gas_compressors.csv` – Compressor specifications

**Format notes:**
- Delimiter auto-detection (comma, semicolon, pipe, tab)
- Column aliases for legacy headers (e.g., "UID" → "uid", "PRmin" → "p_min_kpa")
- Unit normalization handled automatically (m→km, bar→kPa, etc.)

See [docs/data-contract.md](docs/data-contract.md) for full specification.

---

## Troubleshooting

### "Case not found"
```bash
python main.py --list-cases
# Check data/ directory has the case as a subdirectory
```

### "Formulation not available"
Valid choices: `weymouth_ogd`, `weymouth_lp_ogd`
```bash
python main.py --formulation weymouth_ogd
```

### "No optimal solution found"
Try reducing load factor:
```bash
python main.py --load-factor 0.5
```

### Test fails: "ValidationError"
Check that node references in pipes match defined nodes:
```python
# In data/<case>/gas_pipes.csv:
# All fromNode and toNode values must exist in gas_nodes.csv
```

### Solver timeout or memory error
For large cases (ZUG_1300nodes):
1. Use linear formulation: `--formulation weymouth_lp_ogd`
2. Reduce load: `--load-factor 0.1`
3. Check Gurobi license and memory

### Results not written
Verify `outputs/` directory is writable:
```bash
touch outputs/test.txt && rm outputs/test.txt
```

---

## Development Notes

### Principles

- **Modularity**: Formulations are plug-and-play; easy to add new ones
- **Schema harmonization**: Alias-based approach tolerates legacy data variations
- **Transparency**: Equations stay close to implementation; minimal abstraction
- **Determinism**: Reproducible runs via fixed seeds and parameter logging
- **Testing**: Data validation and end-to-end pipeline coverage

### Adding a New Formulation

1. Create `src/new_formulation/` with modules:
   - `variables.py`, `constraints.py`, `objective.py`, `model.py`, `results.py`, `chart.py`
2. Register in `src/formulation_registry.py`
3. Add test case in `tests/`

---

## License

See [LICENSE](LICENSE) file for details.

---

## References

- Gurobi documentation: https://www.gurobi.com/documentation/
- Problem specification: [docs/problem-spec.md](docs/problem-spec.md)
- Data contract: [docs/data-contract.md](docs/data-contract.md)
