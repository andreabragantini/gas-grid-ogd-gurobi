# -*- coding: utf-8 -*-
"""
@author: andrea
"""

import gurobipy as gb
import numpy as np
import pandas as pd
from collections import defaultdict
import Data_Load
import Lib_Variables
import Lib_ObjFnct
import Lib_Charts
import Build_constraints
import Lib_ResExtr


class expando(object):
    pass

resultsdict = defaultdict(object)

# Create a Pandas Excel writer using XlsxWriter as the engine.
writer = pd.ExcelWriter('SensitivityAnalysis_P.xlsx', engine='xlsxwriter')

for p in np.linspace(1,5,5,endpoint=True, dtype=int):
        
    class GasDispatch():
        def __init__(self):        
            self.data = expando()        
            self.variables = expando()
            self.constraints = expando()
            self.results = expando()
            self._load_data()            
            self._build_model_Gas()
                          
                       
        def _load_data(self):
            self.data.pressurediscretization = p
    
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
            Lib_Charts.build_Weymouth3D(self)
            
        def optimize(self):
            self.model.optimize()        
         
    Gasflow = GasDispatch()
    Gasflow.optimize()
    Gasflow.model.params.OutputFlag = 0
    Gasflow._build_results()
    Gasflow._build_charts()
    resultsdict[p] = [Gasflow.results.supplyNG, Gasflow.results.gasflow, Gasflow.results.nodepressure]

    # Position the dataframes in the worksheet.
    Gasflow.results.supplyNG.to_excel(writer, sheet_name='P_{0}'.format(p))
    Gasflow.results.gasflow.to_excel(writer, sheet_name='P_{0}'.format(p), startcol = 3)
    Gasflow.results.nodepressure.to_excel(writer, sheet_name='P_{0}'.format(p), startcol = 6)
    
    # Get the xlsxwriter workbook and worksheet objects.
    workbook  = writer.book
    worksheet = writer.sheets['P_{0}'.format(p)]
    
#        # Create a chart object.
#        chart = workbook.add_chart({'type': 'column'})
#        
#        # Configure the series of the chart from the dataframe data.
#        chart.add_series({'values': '=Sheet1!$B$2:$B$8'})
#        
#        # Insert the chart into the worksheet.
#        worksheet.insert_chart('D2', chart)
            
# Close the Pandas Excel writer and output the Excel file.
writer.save()