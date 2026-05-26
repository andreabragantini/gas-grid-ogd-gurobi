# -*- coding: utf-8 -*-
"""
Created on Thu Sep 29 23:01:23 2016

@author: stde
"""

#==============================================================================
#  Data Loading  
#==============================================================================

import pandas as pd
import numpy as np
import gurobipy as gb
import defaults
import math
from collections import defaultdict
from itertools import chain

def _load_network(self):
    self.data.nodedf = pd.read_csv(defaults.nodefile).set_index('ID')
    self.data.pipedf = pd.read_csv(defaults.linefile).set_index(['fromNode', 'toNode'])
    
	## Node and edge ordering
    self.data.nodeorder = self.data.nodedf.index.tolist()
    self.data.pipeorder = [tuple(x) for x in self.data.pipedf.index]
    
    ## Pipe Data
    pipedata =  self.data.pipedf
    # approximated equation for friction factor ff
    pipedata["Diameter"] = pipedata["Diameter"]    # Unit conversion if needed
    pipedata['Length'] = pipedata['Length']        # Unit conversion if needed
    pipedata['ff'] = 4/(11.18*pipedata['Diameter'].pow(1/6)).pow(2)
    
    Tb = 273
    Pb = 101
    Ta = 300
    Za = 0.9
    G = 0.6
    e = 0.9
    const = 0.0011493

    # approximated formula for gas flow constant (NEW)
    pipedata['Kmu'] = (const*Tb/Pb*pipedata['Diameter']**2.5*e/(pipedata['Length']*G*Ta*Za*pipedata['ff'])**0.5)/24/1000
    
	## Nodes Data
    self.data.nodes = self.data.nodedf['Node'].unique().tolist()
    
    self.data.nodepressranges = defaultdict(list)    
    for m in self.data.nodeorder:
        self.data.nodepressranges[m] = [self.data.nodedf['PRmax'][m],self.data.nodedf['PRmin'][m]]
   
    ## Network Configuration
    self.data.nodetooutpipes = defaultdict(list)
    self.data.nodetoinpipes = defaultdict(list)

    for l in self.data.pipeorder:
        self.data.nodetooutpipes[l[0]].append(l)
        self.data.nodetoinpipes[l[1]].append(l)
        
       
def _load_supplyNG_data(self):
    self.data.supplyunitinfo = pd.read_csv(defaults.supplyunitfile, index_col=0)
    self.data.supplyunits = self.data.supplyunitinfo.index.tolist()
    
    # Mapping - Node (Key) to SupplyUnit (Value)      
    self.data.Map_N2Ss = defaultdict(list)
    # Mapping - SupplyUnit (Key) to Nodes (Value)       
    self.data.Map_S2Ns = defaultdict(list)      
    
    origodict = self.data.supplyunitinfo['Origin']
    for gen, n in origodict.iteritems():
        self.data.Map_S2Ns[gen].append(n)
        self.data.Map_N2Ss[n].append(gen)    
      
def _load_load_data(self):
    self.data.load = self.data.nodedf['Load']
    

def _load_fixed_press_data(self):
    
    self.data.V = defaultdict(list)
    
    for l in self.data.pipeorder:
        
        m1,m2 = l
        
        for i in np.linspace(self.data.nodepressranges[m1][1],self.data.nodepressranges[m1][0], self.data.pressurediscretization, endpoint=True):
            for j in np.linspace(self.data.nodepressranges[m2][1],self.data.nodepressranges[m2][0], self.data.pressurediscretization, endpoint=True):
                if i > j:
                    self.data.V[l] += [(i,j)]
        
# Find a better tool instead of range
# Create a list of list instead of matrix and add tuple values
# Do the selection of feasible couples in the list before, and get rid of the others

# Here we need to create the matrix Vij for each pipeline in the network
# All possible known values of pressure that start/end nodes of the pipe can assume are the elements of the matrix Vij (Mi,Uj) couples
# Needed as input :
# - max and min values of pressure that a node can have (to be used as extremities in the possible values
# - decide in how many blocks you want to split the possible range and assign the elements of Vij 
    
	
