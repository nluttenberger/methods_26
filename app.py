import streamlit as st
import pygraphviz as pgv
from pyvis.network import Network
import streamlit.components.v1 as components

# Seitenkonfiguration für ein breiteres Layout
st.set_page_config(page_title="Interaktives Netzwerk", layout="wide")

st.title("🕸️ Mein interaktives PyGraphviz-Netzwerk")
st.write("Ziehen Sie die Knoten mit der Maus, nutzen Sie das Mausrad zum Zoomen!")

# 1. Netzwerkstruktur mit PyGraphviz definieren
A = pgv.AGraph(directed=True)

# Beispiel-Daten hinzufügen (Knoten und Kanten)
A.add_edge("Datenquelle", "Datenvorbereitung", color="blue")
A.add_edge("Datenvorbereitung", "KI-Modell", color="green")
A.add_edge("KI-Modell", "Dashboard", color="orange")
A.add_edge("KI-Modell", "API-Schnittstelle", color="purple")
A.add_edge("Dashboard", "Benutzer", color="red")
A.add_edge("API-Schnittstelle", "Benutzer", color="red")

# 2. PyGraphviz in eine interaktive Pyvis-Grafik umwandeln
# Hinweis: Falls pyvis fehlt, im Terminal kurz: pip install pyvis
net = Network(height="600px", width="100%", notebook=False, directed=True)

# Knoten übertragen
for node in A.nodes():
    net.add_node(node, label=node, size=25, shape="ellipse")

# Kanten übertragen
for edge in A.edges():
    # edge[0] ist der Startknoten, edge[1] der Zielknoten
    net.add_edge(edge[0], edge[1], arrows="to")

# Physik-Simulation aktivieren (für das elastische Federn beim Ziehen)
net.toggle_physics(True)

# 3. HTML generieren
html_string = net.generate_html()

# 4. In Streamlit einbetten
components.html(html_string, height=620)

st.success("Graph erfolgreich geladen!")
