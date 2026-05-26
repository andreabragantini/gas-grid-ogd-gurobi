# gas-grid-ogd-gurobi
Modular Optimal Gas Dispatch (OGD) framework for gas distribution networks using Gurobi. Implements multiple linear formulations and pressure discretizations. Designed for benchmarking, research, and analysis of gas dispatch distribution networks.


This repo models the simple gas dispatch problem with LINEAR PROGRAMMING.
The network is small and simplified.
The minimization of cost in the objective function does not really matter and the solution is defined mostly by the mass balance constraints which ensure the gasflows in the network and satisfy loads.

All the purpose of this model is to prove the formulation for the bidirectionality of gas flows.


Here the script still uses the "old" notation for pipelines ('fromNode','toNode')
All il indexed with the tuple.