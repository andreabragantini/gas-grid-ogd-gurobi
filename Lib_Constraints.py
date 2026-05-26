	# -*- coding: utf-8 -*-
"""
@author: andrea
"""
import gurobipy as gb
import math
from collections import defaultdict

    
#===========================================================================
# Gas Dispatch problem constraints
#==============================================================================

def build_MassBal_constr(self):
    MassBal = {}
    var = self.variables
    
    for m in self.data.nodes:
        MassBal[m] = self.model.addConstr(
        gb.quicksum(var.supplyNG[k] for k in self.data.Map_N2Ss[m]), 
        gb.GRB.EQUAL,
        self.data.load[m]  +
        gb.quicksum(var.gasflow[l] for l in self.data.nodetooutpipes[m]) -
        gb.quicksum(var.gasflow[l] for l in self.data.nodetoinpipes[m]),  
        name = 'Mass_Balance_Gas({0})'.format(m))


    return MassBal
	
def build_SupplyMax_constr(self):
    SupplyMax = {}
    var = self.variables    
    supplyunits = self.data.supplyunits
    supplyNGdata = self.data.supplyunitinfo   
    
    for k in supplyunits:  
            SupplyMax[k] = self.model.addConstr(var.supplyNG[k], 
            gb.GRB.LESS_EQUAL, 
            supplyNGdata.Capacity[k],
            name = 'Max_Capacity_Supply({0})'.format(k))                

    return SupplyMax

                
def build_pressure_constr(self):
    var = self.variables
    nodedata = self.data.nodedf
    pressure_lim_upper={}
    pressure_lim_lower={}
    
    for m in self.data.nodes:
        pressure_lim_upper[m] = self.model.addConstr(
        var.nodepressure[m] <= nodedata.PRmax[m],
        name = 'Pressure_lim_upper{0}'.format(m))

    for m in self.data.nodes:
        pressure_lim_lower[m] = self.model.addConstr(
        var.nodepressure[m] >= nodedata.PRmin[m],
        name = 'Pressure_lim_lower{0}'.format(m))

    return pressure_lim_lower, pressure_lim_upper


# Set of constriants for Bidirectionality of flows
    
def build_bideractionality_constr(self):
    var = self.variables
    pipelines = self.data.pipeorder
    
    gasflow_def = {}
    q_plus_upper = {}
    q_plus_lower = {}
    q_min_upper = {}
    q_min_lower = {}
    
    for l in pipelines:
        gasflow_def[l] = self.model.addConstr(
                var.gasflow[l],
                gb.GRB.EQUAL,
                var.q_plus[l] - var.q_min[l],
                name = 'Gasflow_main_def_({0})'.format(l))

        q_plus_upper[l] = self.model.addConstr(
                var.q_plus[l],
                gb.GRB.LESS_EQUAL,
                self.data.M*var.y[l],
                name = 'q_plus_upper_constr_{0}'.format(l))
        
        q_plus_lower[l] = self.model.addConstr(
                var.q_plus[l],
                gb.GRB.GREATER_EQUAL,
                0,
                name = 'q_plus_lower_constr_{0}'.format(l))

        q_min_upper[l] = self.model.addConstr(
                var.q_min[l],
                gb.GRB.LESS_EQUAL,
                self.data.M*(1-var.y[l]),
                name = 'q_min_upper_constr_{0}'.format(l))
        
        q_min_lower[l] = self.model.addConstr(
                var.q_min[l],
                gb.GRB.GREATER_EQUAL,
                0,
                name = 'q_min_lower_constr_{0}'.format(l))
	
    return 	gasflow_def, q_plus_upper, q_plus_lower, q_min_upper, q_min_lower
	
	
def build_gasflow_to_press_constr(self):
    var = self.variables
    pipelines = self.data.pipeorder
    pipedata = self.data.pipedf
    q_plus_to_pressure = defaultdict(dict)
    q_min_to_pressure = defaultdict(dict)
	
    for l in pipelines:
        m1, m2 = l
        
        for v in self.data.V[l]:
            
            PRmv, PRuv = v   		
            q_plus_to_pressure[l][v] = self.model.addConstr(
                    var.q_plus[l],
                    gb.GRB.LESS_EQUAL,
                    (pipedata.Kmu[l]*PRmv/math.sqrt(PRmv**2-PRuv**2))*var.nodepressure[m1] -
                    (pipedata.Kmu[l]*PRuv/math.sqrt(PRmv**2-PRuv**2))*var.nodepressure[m2] +
                    self.data.M*(1 - var.y[l]),
                    name = 'Qplus_def_pipe{0}_values{1}'.format(l,v))

            q_min_to_pressure[l][v] = self.model.addConstr(
                    var.q_min[l],
                    gb.GRB.LESS_EQUAL,
                    (pipedata.Kmu[l]*PRmv/math.sqrt(PRmv**2-PRuv**2))*var.nodepressure[m1] -
                    (pipedata.Kmu[l]*PRuv/math.sqrt(PRmv**2-PRuv**2))*var.nodepressure[m2] +
                    self.data.M*var.y[l],
                    name = 'Qmin_def_pipe{0}_values{1}'.format(l,v))
    
    return q_min_to_pressure, q_plus_to_pressure
