# -*- coding: utf-8 -*-
"""
@author: andrea
"""
import gurobipy as gb



#==============================================================================
# OPF variables
#==============================================================================

def build_variables_Gas(self):      

    var = self.variables
    nodes = self.data.nodes      
    supplyunits = self.data.supplyunits
    pipelines = self.data.pipeorder
	
   # NG supply units
    var.supplyNG = {}
    for k in supplyunits:
        var.supplyNG[k] = self.model.addVar(lb=0.0, name = 'SupplyUnit({0})'.format(k))
                        
   # Nodal phase angles  
    var.nodepressure = {}
    for m in nodes:
        var.nodepressure[m] = self.model.addVar(lb=-gb.GRB.INFINITY, ub=gb.GRB.INFINITY, name='nodepressure({0})'.format(m))
	
    # Pipelines flow                
    var.gasflow = {}
    for l in pipelines: 
        var.gasflow[l] = self.model.addVar(lb=-gb.GRB.INFINITY, ub=gb.GRB.INFINITY, name='gasflow({0})'.format(l))
          
    # Gasflow directionality auxiliary variables
    var.q_plus = {}
    for l in pipelines:
        var.q_plus[l] = self.model.addVar(lb=-gb.GRB.INFINITY, ub=gb.GRB.INFINITY, name='q_plus_({0})'.format(l))
       
    var.q_min = {}
    for l in pipelines:
        var.q_min[l] = self.model.addVar(lb=-gb.GRB.INFINITY, ub=gb.GRB.INFINITY, name='q_min_({0})'.format(l))
    
    var.y = {}
    for l in pipelines:
        var.y[l] = self.model.addVar(vtype=gb.GRB.BINARY, name='Directionality_bin_var_({0})'.format(l))

    self.model.update()