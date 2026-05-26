# -*- coding: utf-8 -*-
"""
@author: andrea
"""

import gurobipy as gb
import Data_Load
import Lib_Variables
import Lib_ObjFnct
import Lib_Charts
import Build_constraints
import Lib_ResExtr
from tabulate import tabulate


class expando(object):
    pass


class GasDispatch():
    def __init__(self):        
        self.data = expando()        
        self.variables = expando()
        self.constraints = expando()
        self.results = expando()
        self._load_data()            
        self._build_model_Gas()
                      
                   
    def _load_data(self):
        self.data.pressurediscretization = 6
        self.data.M = 10000

        Data_Load._load_network(self)     
        Data_Load._load_supplyNG_data(self)
        Data_Load._load_load_data(self)
        Data_Load._load_fixed_press_data(self)
        
        
    def _build_model_Gas(self):
        self.model = gb.Model()        

        Lib_Variables.build_variables_Gas(self)
        Build_constraints._build_constraints_Gas(self)   
        Lib_ObjFnct.build_objective_Gas(self)
        
        self.model.update()
    
    def _build_results(self):
        Lib_ResExtr.build_results_Gas(self)
    
    def _build_charts(self):
        Lib_Charts.build_networkchart(self)
        #Lib_Charts.build_Weymouth3D(self)
        
    def optimize(self):
        self.model.optimize()        
        
        
GasSimple = GasDispatch()

try:
    GasSimple.optimize()

    GasSimple._build_results()
    GasSimple._build_charts()
    
    # Print Results
    print('##################### Gas Network Results #####################')
    print(tabulate(GasSimple.results.nodepressure, headers='keys', tablefmt='psql'))
    print(tabulate(GasSimple.results.supplyNG, headers='keys', tablefmt='psql'))
    print(tabulate(GasSimple.results.gasflow, headers='keys', tablefmt='psql'))
    print(tabulate(GasSimple.results.q_plus, headers='keys', tablefmt='psql'))
    print(tabulate(GasSimple.results.q_min, headers='keys', tablefmt='psql'))
    print(tabulate(GasSimple.results.y, headers='keys', tablefmt='psql'))
    print('###############################################################')

except:
    print("######## Model is not feasible")