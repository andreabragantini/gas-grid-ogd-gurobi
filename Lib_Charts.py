# -*- coding: utf-8 -*-
"""
@author: andrbrag
"""

import numpy as np
import pandas as pd
from collections import defaultdict
import plotly
import plotly.graph_objs as go
import matplotlib.pyplot as plt
import networkx as nx
	
def build_networkchart(self):
    A = nx.Graph()
    A.add_nodes_from(self.data.nodes)
    A.add_edges_from(self.data.pipeorder, color = 'blue')
	
    edges = A.edges()
    colors = [A[u][v]['color'] for u,v in edges]
	
    plt.title('Current Network')
    plt.legend(colors)
    nx.draw(A, with_labels=True, edge_color=colors)
    plt.show()

def build_Weymouth3D(self):
    tracesdict = defaultdict(object)
    z_weymouth = pd.DataFrame()
    z_data = defaultdict(object)
    
    l = ('m1','m2')
   
    for i in np.linspace(self.data.nodepressranges[l[0]][1],self.data.nodepressranges[l[0]][0], 20, endpoint=True):
            for j in np.linspace(self.data.nodepressranges[l[1]][1],self.data.nodepressranges[l[1]][0], 20, endpoint=True):
                if i >= j:
                    z_weymouth.loc[i,j] = self.data.Kmu[l]*np.sqrt(i**2-j**2)
                else :
                    continue
            
    weymouth = go.Surface(
        z=z_weymouth.values,
        opacity=0.95
    )
    
    
    for v in self.data.V[l]:
        
        PRmv, PRuv = v
        z_data[v] = pd.DataFrame()
        
        for i in np.linspace(self.data.nodepressranges[l[0]][1],self.data.nodepressranges[l[0]][0], 20, endpoint=True):
            for j in np.linspace(self.data.nodepressranges[l[1]][1],self.data.nodepressranges[l[1]][0], 20, endpoint=True):
                z_data[v].loc[i,j] = (self.data.Kmu[l]*PRmv/np.sqrt(PRmv**2-PRuv**2))*i -(self.data.Kmu[l]*PRuv/np.sqrt(PRmv**2-PRuv**2))*j
        
        tracesdict[v] = go.Surface(
                z=z_data[v].values,
                opacity=0.5)
                
    traces = [tracesdict[v] for v in tracesdict.keys()]
    
    data = [weymouth] + traces
    layout = go.Layout(
            title='Weymouth Equation',               
            margin=dict(
                l=65,
                r=50,
                b=65,
                t=90    ),
            scene={ "xaxis": {'title': "Pressure of downstream node",
                                              "tickfont": {"size": 10}, 'type': "linear"},
                    "yaxis": {"title": "Pressure of upstream node",
                              "tickfont": {"size": 10}, "tickangle": 1},
                    "zaxis": {'title': "Gas flow admitted",
                              "tickfont": {"size": 10}}}
    )
    
    fig = go.Figure(data=data, layout=layout)
    plotly.offline.plot(fig, filename='WeymouthEq3D_P{0}.html'.format(self.data.pressurediscretization))




