# -*- coding: utf-8 -*-
"""
Created on Wed Feb 15 11:05:23 2017

@author: stde
"""

import pandas as pd


def build_results_Gas(self):
    
    supplyunits = self.data.supplyunits
    pipelines = self.data.pipeorder
    nodes = self.data.nodes
    
    self.results.supplyNG = pd.DataFrame(
        [self.variables.supplyNG[k].x for k in supplyunits], index=supplyunits, columns=['SupplyNG [Nm3/h]'])
       
    self.results.nodepressure = pd.DataFrame(
        [self.variables.nodepressure[m].x for m in nodes], index=nodes, columns=['Pressure [KPa]'])

    self.results.gasflow = pd.DataFrame(
        [self.variables.gasflow[l].x for l in pipelines], index=pipelines, columns=['GasFlow [Nm3/h]'])

    self.results.q_plus = pd.DataFrame(
        [self.variables.q_plus[l].x for l in pipelines], index=pipelines, columns=['Qplus [Nm3/h]'])

    self.results.q_min = pd.DataFrame(
        [self.variables.q_min[l].x for l in pipelines], index=pipelines, columns=['Qminus [Nm3/h]'])

    self.results.y = pd.DataFrame(
        [self.variables.y[l].x for l in pipelines], index=pipelines, columns=['Direction'])