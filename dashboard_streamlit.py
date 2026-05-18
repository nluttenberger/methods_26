import streamlit as st
import networkx as nx
import io
import zipfile
from graphviz_utils import layout_and_render

st.set_page_config(layout="wide", page_title="Graphviz Layout Comparison")

def build_dot(G, config):
    lines = [f'digraph G {{\n    graph [margin="{config.get("margin",0.2)}"];']
    if config.get('rankdir'):
        lines.append(f'    rankdir={config["rankdir"]};')
    for n, data in G.nodes(data=True):
        label = data.get('label', str(n))
        attrs = [f'label="{label}"']
        if config.get('fixedsize'):
            attrs.append('fixedsize=true')
            if config.get('width'):
                attrs.append(f'width={config["width"]}')
            if config.get('height'):
                attrs.append(f'height={config["height"]}')
        lines.append(f'    "{n}" [{", ".join(attrs)}];')
    for u, v in G.edges():
        lines.append(f'    "{u}" -> "{v}";')
    lines.append('}\n')
    return '\n'.join(lines)

def sample_graph():
    G = nx.DiGraph()
    for i in range(1,11):
        G.add_node(i, label=("Node %d" % i))
    edges = [(1,2),(1,3),(2,4),(2,5),(3,6),(5,7),(5,8),(6,9),(9,10),(4,10),(7,10),(8,10)]
    G.add_edges_from(edges)
    # add varying label lengths to provoke autosizing
    G.nodes[3]['label'] = 'A very long label to force autosize behavior'
    G.nodes[7]['label'] = 'S'
    G.nodes[10]['label'] = 'Terminal Node'
    return G

st.title('Graphviz Layout Engine Comparison (dot vs fdp)')

with st.sidebar:
    st.header('Global options')
    engine = st.selectbox('Engine', ['dot','fdp'])
    random_seed = st.number_input('Random seed', min_value=0, value=42)
    st.markdown('---')
    st.header('Graph')
    sample = st.button('Load sample graph')
    nodes = st.slider('Node count (when random)', 3, 40, 10)
    gen_random = st.button('Generate random graph')

if 'G' not in st.session_state:
    st.session_state.G = sample_graph()

if sample:
    st.session_state.G = sample_graph()
if gen_random:
    import random
    G = nx.gnm_random_graph(nodes, nodes*2, seed=random_seed, directed=True)
    # add labels of varying lengths
    for n in G.nodes():
        G.nodes[n]['label'] = ('Node %d' % n) + ('\n' + 'x'* (n % 12))
    st.session_state.G = G

G = st.session_state.G

st.sidebar.markdown('---')
st.sidebar.header('Config A')
def config_panel(prefix='A'):
    c = {}
    c['fixedsize'] = st.sidebar.checkbox(f'Fixed size ({prefix})', value=False)
    c['width'] = st.sidebar.number_input(f'Width ({prefix})', min_value=0.0, value=0.7, step=0.1)
    c['height'] = st.sidebar.number_input(f'Height ({prefix})', min_value=0.0, value=0.5, step=0.1)
    c['margin'] = st.sidebar.number_input(f'Margin ({prefix})', min_value=0.0, value=0.2, step=0.05)
    c['rankdir'] = st.sidebar.selectbox(f'Rankdir ({prefix})', [None,'LR','TB'])
    return c

configA = config_panel('A')
st.sidebar.markdown('---')
st.sidebar.header('Config B')
configB = config_panel('B')

st.sidebar.markdown('---')
st.sidebar.header('Visualization')
show_bboxes = st.sidebar.checkbox('Show layout bounding boxes', value=True)
auto_labels = st.sidebar.checkbox('Auto-size labels (override fixedsize)', value=True)

col1, col2 = st.columns(2)

def render_config(config, title):
    dot = build_dot(G, config if not auto_labels else {**config, 'fixedsize': False})
    svg, plain = layout_and_render(dot, engine=engine, annotate_bboxes=show_bboxes)
    return svg, plain

with col1:
    st.subheader('Config A')
    svgA, plainA = render_config(configA, 'A')
    st.components.v1.html(svgA, height=600)
    with st.expander('Layout log A'):
        st.text(plainA)

with col2:
    st.subheader('Config B')
    svgB, plainB = render_config(configB, 'B')
    st.components.v1.html(svgB, height=600)
    with st.expander('Layout log B'):
        st.text(plainB)

st.markdown('---')
st.header('Export results')
if st.button('Export comparison (zip of SVGs + logs)'):
    mem = io.BytesIO()
    z = zipfile.ZipFile(mem, 'w')
    z.writestr('configA.svg', svgA)
    z.writestr('configB.svg', svgB)
    z.writestr('logA.txt', plainA)
    z.writestr('logB.txt', plainB)
    z.close()
    mem.seek(0)
    st.download_button('Download ZIP', mem, file_name='graphviz_comparison.zip')
