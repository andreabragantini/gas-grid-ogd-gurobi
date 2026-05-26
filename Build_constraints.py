# -*- coding: utf-8 -*-
"""
@author: andrea
"""

    
def _build_constraints_Gas(self):
    
           
    from Lib_Constraints import  \
        build_SupplyMax_constr, build_MassBal_constr , \
        build_gasflow_to_press_constr, build_pressure_constr, \
        build_bideractionality_constr
        
    self.constraints.MassBalance = build_MassBal_constr(self)
    self.constraints.SupplyMax = build_SupplyMax_constr(self)
    self.constraints.Pressure = build_pressure_constr(self)
    self.constraints.WeymouthEq = build_gasflow_to_press_constr(self)
    self.constraints.bidirection = build_bideractionality_constr(self)