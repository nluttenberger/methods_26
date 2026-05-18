import streamlit as st
import pygraphviz as pgv

st.title("DOT-String mit PyGraphviz verarbeiten")

# 1. Ein bestehender DOT-String (z. B. aus einer Datenbank oder Datei)
alter_dot_string = """
digraph G {
    "Eingang" -> "Station A";
    "Station A" -> "Ausgang";
}
"""

# 2. Den DOT-String in ein PyGraphviz-Objekt laden
graph = pgv.AGraph(string=alter_dot_string)

# 3. Den Graphen dynamisch in Python manipulieren
# Wir fügen einen neuen Knoten und eine neue Kante hinzu
graph.add_node("Zusatzschritt", color="red", style="filled", fillcolor="lightpink")
graph.add_edge("Station A", "Zusatzschritt")
graph.add_edge("Zusatzschritt", "Ausgang")

# 4. Den modifizierten Graphen wieder als DOT-String exportieren
neuer_dot_string = graph.string()

# 5. In Streamlit anzeigen
st.graphviz_chart(neuer_dot_string)
