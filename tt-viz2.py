import streamlit as st
import networkx as nx
from pyvis.network import Network
import pygraphviz as pgv

G = nx.karate_club_graph()
print(G)

net = Network(height="700px", width="100%", bgcolor="white", font_color="black")
net.from_nx(G)
net.write_html("graph.html", open_browser=False)

st.html("graph.html", width="stretch")