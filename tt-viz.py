import streamlit as st
import networkx as nx
import pydot
import json
import math
from collections import Counter

##### Helper functions for graph visualization

# Functions to compute node attributes

dark = False
directory_path_in = "./misc/"
with open(f"{directory_path_in}meta.json", 'r', encoding='utf-8') as f:
    meta = json.load(f)
    f.close()
#print(meta)

#node_coloring = "node coloring: party"
node_coloring = "node coloring: year"

def computeNodeFillcolor_party(att):
    global dark
    xx = att['used_in']
    y = [meta[x]['party'] for x in xx]
    z = dict(Counter(y))
    if 'Republikaner' in z and 'Demokrat' in z:
        return 'Thistle'
    elif 'Republikaner' in z:
        dark = True
        return '#E9141D'
    elif 'Demokrat' in z:
        dark = True
        return '#0015BC'
    else:
        return 'lightblue'

def computeNodeFillcolor_year(att):
    global dark
    xx = att['used_in']
    ix = xx[0].split('_')
    year = ix[-1]
    #print(year)
    blue2yellow = [('#081d58ff','dark'), ('#253494ff', 'dark'), ('#225ea8ff', 'dark'), ('#1d91c0ff', 'light'), \
                   ('#41b6c4ff', 'light'), ('#7fcdbbff', 'light'), ('#c7e9b4ff', 'light'), ('#edf8b1ff', 'light'), ('#ffffd9ff', 'light')]
    pastell   = [('#fbb4aeff', 'light'), ('#b3cde3ff', 'light'), ('#ccebc5ff', 'light'), ('#decbe4ff', 'light'), \
                 ('#fed9a6ff', 'light'), ('#ffffccff', 'light'), ('#e5d8bdff', 'light'), ('#fddaecff', 'light'), ('#f2f2f2ff', 'light')]
    palette = blue2yellow
    if year == '1789' or year == '1793':  # G. Washington's addresses
        if palette[0][1] == "dark":
            dark = True
        return palette[0][0]
    elif year >  '1793' and year < '1805':
        if palette[1][1] == "dark":
            dark = True
        return palette[1][0]
    elif year >= '1805' and year < '1833':
        if palette[2][1] == "dark":
            dark = True
        return palette[2][0]
    elif year >= '1833' and year < '1866':
        if palette[3][1] == "dark":
            dark = True
        return palette[3][0]
    elif year >= '1866' and year < '1905':
        if palette[4][1] == "dark":
            dark = True
        return palette[4][0]
    elif year >= '1905' and year < '1933':
        if palette[5][1] == "dark":
            dark = True
        return palette[5][0]
    elif year >= '1933' and year < '1965':
        if palette[6][1] == "dark":
            dark = True
        return palette[6][0]
    elif year >= '1965' and year < '2001':
        if palette[7][1] == "dark":
            dark = True
        return palette[7][0]
    elif year >= '2001':
        if palette[8][1] == "dark":
            dark = True
        return palette[8][0]
    else:
        return 'lightblue'
    
def computeNodeFillcolor(att):
    if node_coloring == "node coloring: party":
        return computeNodeFillcolor_party(att)
    else:
        return computeNodeFillcolor_year(att)
    
def computeNodeWidth(att):
    #print(att.get('term_frq'), att.get('id'))
    w  = 1.0 + math.sqrt(0.2*(att.get('term_frq')-1))
    return w

def computeNodeFontcolor():
    global dark
    if dark:
        dark = False
        return 'white'
    else:
        return 'black'
    
def computeNodeTooltip(att):
    xx = str(att['used_in'])
    return xx.replace("[", "").replace("]", "").replace(", ", "\n")

# Functions to compute edge attributes

def computeEdgePenwidth(att):
    return str(att.get('weight')) 

def computeEdgeColor(att):
    if att.get('weight') > 1:
        return 'red'
    else:
        return 'black'

def graphToDot(graph=None):

   #dot file header
   dot  = 'graph {\n   overlap="prism1000"\n   rankdir="LR"\n   outputorder="edgesfirst" splines="false"\n'
   dot += '   fontsize="80"\n   fontname="Arial"\n   labelloc="t"\n   labeljust="l"'
   dot += '   node [margin=0 fontname="Arial" fontcolor="black" fontsize=64 shape=circle style=filled];\n'
   # edges
   for u,v,att in graph.edges(data=True):
      dot += f'   {u} -- {v} [id="{u}--{v}"'
      dot += f' penwidth={computeEdgePenwidth(att)}'
      dot += f' color="{computeEdgeColor(att)}"]\n'
   #nodes
   for u,att in graph.nodes(data=True):
      dot += f'   {u} [id="{u}"'
      dot += f' fillcolor="{computeNodeFillcolor(att)}"'  
      dot += f' fontcolor="{computeNodeFontcolor()}"' 
      dot += f' width={computeNodeWidth(att)}' 
      dot += f' tooltip="{computeNodeTooltip(att)}"]\n'
   # close dot string
   dot += '}'
   return dot

##### Main program

# Reconstruct the graph
with open('graphs/USPresInaugAddr_0.14.json', 'r', encoding='utf-8') as f:
    InaugAddr_json = json.load(f)
G = nx.node_link_graph(InaugAddr_json)

# Convert graph to dot format
dot = graphToDot(G)

# Render graph in streamlit
st.container(width=2400).graphviz_chart(dot)