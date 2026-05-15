## Overview

This project implements and compares four branching strategies for Mixed-Integer Programming:
- **Random** — selects a fractional variable uniformly at random
- **Pseudocost** — scores variables by historical objective gain estimates
- **Strong** — evaluates candidate variables by solving child LP relaxations
- **Reliability** — uses pseudocosts for well-observed variables, falls back to strong branching otherwise

Experiments are run using [SCIP](https://www.scipopt.org/) via PySCIPOpt on MIPLIB 2017 benchmark instances.

## Requirements

pip install pyscipopt numpy pandas matplotlib

Python 3.10+ recommended.

## Project Structure

```
Final_Project/
├── final_project_code.py   
├── plot_results.py         
├── results.csv             
├── instances/              
│   ├── air05.mps
│   ├── cap6000.mps
│   ├── fiber.mps
│   ├── gen.mps
│   └── misc07.mps
├── plot_nodes.png
├── plot_runtime.png
├── plot_time_per_node.png
├── plot_fair_node_number.png
└── README.md
```

## Getting the Instances

Download the following instances from [MIPLIB 2017](https://miplib.zib.de/):
- [air05]
- [cap6000]
- [fiber]
- [gen]
- [misc07]

You can look up each individual instance or download all the instances from MIPLIB and then select the respective folders.

Extract and place the `.mps` files in the `instances/` folder.

## Reproducing Results

Run each strategy separately. Results are appended to `results.csv` and already-completed runs are skipped automatically:

```bash
python final_project_code.py --strategy default
python final_project_code.py --strategy random
python final_project_code.py --strategy pseudocost
python final_project_code.py --strategy strong
python final_project_code.py --strategy reliability
```

Optional arguments:
- `--time_limit` — time limit per instance in seconds (default: 600)
- `--out` — output CSV file (default: results.csv)

Example with custom time limit:
```bash
python final_project_code.py --strategy strong --time_limit 300
```

## Generating Plots

Once all strategies are done:
```bash
python plot_results.py
```

This saves four plots to the project directory:
- `plot_nodes.png` — B&B node count by instance and strategy
- `plot_runtime.png` — wall-clock runtime by instance and strategy
- `plot_time_per_node.png` — runtime per node by instance and strategy
- `plot_fair_node_number.png` — fair node number by instance and strategy

## Notes

- All runs use a single thread for fair comparison
- fiber and gen solve at the root node (1 node) and are excluded from analysis
- bnatt500 and neos-5107597-kakapo exceeded the time limit without finding feasible solutions and are excluded
- Node counts were identical across all strategies due to SCIP's presolve and cutting planes dominating tree structure; analysis focuses on runtime and per-node cost

## Reference

Gamrath et al., *Measuring the Impact of Branching Rules for Mixed-Integer Programming*, Operations Research Proceedings, 2018.