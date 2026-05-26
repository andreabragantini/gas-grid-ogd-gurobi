# -*- coding: utf-8 -*-
"""
Created on Sat Oct 01 13:37:04 2016

Library of Objective Functions

@author: stde
"""
import gurobipy as gb

        
def build_objective_Gas(self):        
    
    supplyunits = self.data.supplyunits
    supplyNGdata = self.data.supplyunitinfo
    pipes = self.data.pipeorder
    pipedata = self.data.pipedf
    var = self.variables
           
    self.model.setObjective(
        gb.quicksum(supplyNGdata.Cost[k]*var.supplyNG[k] for k in supplyunits) + 
        0.001*gb.quicksum(var.nodepressure[l[0]] -
                             var.nodepressure[l[1]] for l in self.data.pipeorder),        
        gb.GRB.MINIMIZE)

''' Cost of natural gas supply is based ona rough average of the gas prices
in the most important european hubs. It is fixed around 200$/TCM 
(thousand cubic meter), so 0.20 $/Nm3.
Mind that price varies according to gas composition and calorific value. '''