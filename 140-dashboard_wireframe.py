from bs4 import BeautifulSoup
import spacy
import streamlit as st
import plotly.figure_factory as ff
from numpy.random import default_rng as rng
import plotly.graph_objects as go
import networkx as nx
from networkx.algorithms import bipartite
import json
import pymongo
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import CountVectorizer
from collections import Counter 
import pandas as pd
import math
import os
import tempfile
import pygraphviz as pgv
from streamlit import components
pd.options.display.max_rows = 600

########## Configuration and constants 

# MongoDB connection URI (set your credentials here)
MONGO_URI = "mongodb+srv://nluttenberger:Ii5K!dQ%40F3txZ3D7@methods26-cluster.f7nz9hl.mongodb.net/?appName=methods26-cluster"

# Historical periods mapping to year ranges
HISTORY_PERIODS = {
    "None": (None, None),
    "Civil War": (1861, 1865),
    "WW-1": (1914, 1918),
    "WW-2": (1939, 1945),
    "Great Depression": (1929, 1939),
    "Cold War": (1947, 1991),
}

# Party label mapping for UI values to stored MongoDB values
PARTY_MAP = {
    "Democrat": ["Demokrat", "Democrat"],
    "Republican": ["Republikaner", "Republican"],
    "Whig": ["Whig"],
    "Federalist": ["Föderalist", "Federalist"],
    "Independent": ["parteilos", "Independent"],
}

# Load stopwords for lemmatization from file
file = 'stopwords/stopwords_en_nl'
with open(file, 'r', encoding='utf-8') as stop:
    stopw = stop.read()
stopw = stopw.split('\n')

# Load spaCy model for NLP processing
nlp = spacy.load("en_core_web_sm")

########## Functions

### Callback function for form submission to set session state
def submitted():
    st.session_state.submitted = True

### Make corpus 
def make_corpus(time=None, history=None, party=None):
    """
    Retrieve inauguration address texts from MongoDB based on filters.
        Parameters:
    - time: tuple (min_year, max_year) from year range slider
    - history: str, historical period name
    - party: str, political party name
    
    Returns:
    - list of documents containing text excerpts matching the filters
    """
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client.myDatabase
        coll = db.inaug_addresses
        print("Connected to MongoDB successfully.")
    except pymongo.errors.ConfigurationError:
        print("Invalid MongoDB URI or connection failed.")
        return []
    
    query_filter = {}
    year_filter = {}

    # Handle year range from time slider
    min_year, max_year = time
    year_filter["$gte"] = str(min_year)
    year_filter["$lte"] = str(max_year)

    # Handle historical period filter
    if history != "None":
        start_year, end_year = HISTORY_PERIODS.get(history, (None, None))
        year_filter["$gte"] = str(start_year)
        year_filter["$lte"] = str(end_year)

    query_filter["year"] = year_filter

    # Handle party filter
    if party != "All":
        mapped = PARTY_MAP.get(party, [party])
        query_filter["party"] = {"$in": mapped}

    print(f"Constructed query filter: {query_filter}")

    try:
        q_cursor = coll.find(query_filter, {
            "_id": 0,
            "addr_id": 1,
            "pres_name": 1,
            "year": 1,
            "party": 1,
            "date": 1,
            "txt": 1
        })
        results = list(q_cursor)
        return results
    except pymongo.errors.OperationFailure as e:
        print(f"Database operation failed: {e}")
        return []
    finally:
        client.close()

### Extract keywords from corpus
def vectorize_corpus(corpus):
    
    """
    Extract keywords from the given corpus of texts using spaCy for NLP processing,
    and TF-IDF for term vectorization. Impose a threshold on the TF-IDF scores to filter relevant keywords.
    Parameters: 
    - corpus: list of documents, each document is a dict with 'txt' field containing the text
    - keyword_score: float, threshold for keyword relevance (not implemented in this example, placeholder for future scoring mechanism)
    Returns:
    - DataFrame with columns 'addr_id', 'text_len', and 'text' containing the processed text for each document
    """

    # Lemmatization
    print(f"Extracting keywords with score threshold: {keyword_score}")
    lemmatized_df = pd.DataFrame(columns=['addr_id', 'text_len', 'text'])
    for doc in corpus:
        content = doc['txt'].lower()
        content = content.replace('\n',' ')
        soup = BeautifulSoup(content, 'html.parser')
        text_no_tags = soup.get_text()
        cleaned = nlp(text_no_tags)
        text_lemmata = [token.lemma_ for token in cleaned if token.text not in stopw and not token.is_punct and not token.lemma_ in stopw]
        text_lemmatized = ' '.join(text_lemmata)
        text = re.sub(r'\$?\s*\d+[,\d+]+', '', text_lemmatized)     
        lemmatized_df.loc[len(lemmatized_df)] = [doc.get('addr_id'), len(text), text]
    lemmatized_df = lemmatized_df.sort_values('addr_id').reset_index(drop=True)

    # TF-IDF vectorization
    addresses = lemmatized_df['text'].tolist()
    text_titles = lemmatized_df['addr_id'].tolist()
    tfidf_vectorizer = TfidfVectorizer(input='content')
    tfidf_vector = tfidf_vectorizer.fit_transform(addresses)
    # Make a DataFrame out of the resulting tf–idf vector, setting the "feature names" (terms) as columns and the address titles (i.e. file names) as rows
    tfidf_df = pd.DataFrame(tfidf_vector.toarray(), index=text_titles, columns=tfidf_vectorizer.get_feature_names_out())
    
    return tfidf_df

### Create bipartite graph from tf-idf DataFrame and set node attributes based on corpus metadata
def create_bipartite_graph(tfidf_df, keyword_score, corpus):
    """
    Create a bipartite graph where one set of nodes represents addresses and the other set represents terms, 
    with edges indicating the presence of a term in an address based on the thresholded TF-IDF values.
    Set node attributes for the bipartite graph, such as party affiliation and year of first use for term nodes, 
    based on the original corpus data.
    Parameters:
    - tfidf_df: DataFrame wiht addresses as rows and terms as columns, containing TF-IDF scores
    - keyword_score: float, threshold for keyword relevance
    - corpus: list of documents containing metadata for addresses
    Returns:
    - B: bipartite graph
    """
    # Reframe the tfidf dataFrame so that the terms are in rows rather than columns.
    stacked_df = tfidf_df.stack().reset_index().rename(columns={0:'tfidf', 'level_0': 'address','level_1': 'term'})

    # Set threshold for TF-IDF values and determine remaining terms
    thres_tfidf = stacked_df[stacked_df['tfidf'] >= float(keyword_score)]
    print ('terms in reduced dataframe: ', len(thres_tfidf['term'].unique()))

    # Create bipartite graph B from the thresholded DataFrame
    B = nx.Graph()
    for _, row in thres_tfidf.iterrows():
        address_node = row['address']
        term_node = row['term']
        B.add_node(address_node, type='address')
        B.add_node(term_node, type='term')
        B.add_edge(address_node, term_node)
    
    # Create a mapping from address ID to party and year
    addr_metadata = {doc['addr_id']: {'party': doc['party'], 'year': int(doc['year'])} for doc in corpus}
    
    # Set attributes for address nodes
    for node in B.nodes():
        if B.nodes[node]['type'] == 'address':
            metadata = addr_metadata.get(node, {})
            B.nodes[node]['party'] = metadata.get('party', 'Unknown')
            B.nodes[node]['year'] = metadata.get('year', None)
    
    # Set attributes for term nodes: year of first use, and party affiliation based on the address with the earliest year of use
    for node in B.nodes():
        if B.nodes[node]['type'] == 'term':
            connected_addresses = [n for n in B.neighbors(node) if B.nodes[n]['type'] == 'address']
            years = [B.nodes[addr].get('year') for addr in connected_addresses if B.nodes[addr].get('year') is not None]
            parties = [B.nodes[addr].get('party') for addr in connected_addresses if B.nodes[addr].get('party') is not None]
            if years:
                B.nodes[node]['year'] = min(years)
            else:
                B.nodes[node]['year'] = None
            B.nodes[node]['party'] = parties[years.index(B.nodes[node]['year'])] if years else None
            B.nodes[node]['used_in'] = connected_addresses
    
    # set attributes for all nodes: degree and doc_freq (number of addresses the term appears in)
    for node in B.nodes():
        if B.nodes[node]['type'] == 'term':
            B.nodes[node]['degree'] = B.degree(node)
            B.nodes[node]['doc_freq'] = create_doc_freq_dict(tfidf_df, keyword_score).get(node)
            print(f"Node: {node}, Year: {B.nodes[node]['year']}, Party: {B.nodes[node]['party']}, Doc freq: {B.nodes[node]['doc_freq']}, Degree: {B.nodes[node]['degree']}")
    return B
    

### Create document frequency dict
def create_doc_freq_dict(tfidf_df, keyword_score):
    """
    Create a dictionary mapping each term to its document frequency (number of addresses it appears in).
    Parameters:
    - tfidf_df: DataFrame with addresses as rows and terms as columns, containing TF-IDF scores
    - keyword_score: float, threshold for keyword relevance
    Returns:
    - doc_freq_dict: dict mapping term to document frequency
    """
    reduced_df = tfidf_df.where(tfidf_df >= float(keyword_score), other=0) # Filter columnwise based on keyword score threshold
    reduced_df.loc['doc_freq'] = reduced_df.mask(reduced_df > 0, 1).sum()
    doc_freq_dict = {k: int(v) for k, v in reduced_df.loc['doc_freq'].to_dict().items()}
    print(reduced_df[['arrive', 'repose', 'punishment', 'magistrate', 'incur', 'official']])
    return doc_freq_dict

### Create keyword graph from bipartite graph by projection
def create_keyword_graph(B):
    """
    Create a keyword graph by projecting the bipartite graph onto the term nodes, 
    where edges between terms indicate co-occurrence in the same address.
       Parameters:
       - B: bipartite graph
       Returns:
       - G: keyword graph
    """
    X = bipartite.weighted_projected_graph(B, [n for n, d in B.nodes(data=True) if d['type'] == 'term'])
    # print (X.nodes(data=True))
    return X

### Node size helper based on document frequency
def compute_node_sizes(G, nodes, node_sizing='doc_freq', node_size_growth='proportional', min_size=10, max_size=50):
    """
    Compute marker sizes for nodes in the graph based on the selected sizing metric.
    Parameters:
    - G: NetworkX graph with node attributes such as 'doc_freq' and degree
    - nodes: ordered list of nodes to compute sizes for
    - node_sizing: 'doc_freq' or 'degree'
    - node_size_growth: 'proportional' or 'radix'
    - min_size: minimum marker size
    - max_size: maximum marker size
    Returns:
    - sizes: list of marker sizes in graph node order
    """
    values = []
    for node in nodes:
        if node_sizing == 'doc_freq':
            values.append(G.nodes[node].get('doc_freq', 0))
        elif node_sizing == 'degree':
            values.append(G.degree(node))
        else:
            values.append(G.degree(node))

    if not values or max(values) == min(values):
        return [min_size for _ in values]

    if node_size_growth == 'radix':
        transformed = [v ** 0.5 for v in values]
    else:
        transformed = values

    min_val = min(transformed)
    max_val = max(transformed)
    range_val = max_val - min_val if max_val != min_val else 1

    sizes = [min_size + (value - min_val) / range_val * (max_size - min_size) for value in transformed]
    return sizes

### Graph visualization function using Plotly and NetworkX
def viz_graph(G=None, node_coloring='by party', node_sizing='doc_freq', node_size_growth='proportional'):
    pos = nx.spring_layout(G)
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines')

    node_degree = dict(G.degree())
    sorted_nodes = sorted(G.nodes(), key=lambda n: node_degree[n])
    node_x = [pos[node][0] for node in sorted_nodes]
    node_y = [pos[node][1] for node in sorted_nodes]
    node_degrees = [node_degree[node] for node in sorted_nodes]
    node_sizes = compute_node_sizes(G, sorted_nodes, node_sizing=node_sizing, node_size_growth=node_size_growth)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        hoverinfo='text',
        marker=dict(
            showscale=True,
            # colorscale options
            #'Greys' | 'YlGnBu' | 'Greens' | 'YlOrRd' | 'Bluered' | 'RdBu' |
            #'Reds' | 'Blues' | 'Picnic' | 'Rainbow' | 'Portland' | 'Jet' |
            #'Hot' | 'Blackbody' | 'Earth' | 'Electric' | 'Viridis' |
            colorscale='YlGnBu',
            color=[],
            size=node_sizes,
            colorbar=dict(
                thickness=15,
                title=dict(
                text='Node degree',
                side='right'
                ),
                xanchor='left',
            ),
            line_width=0.5))

    if node_coloring == 'by party':
        parties = [G.nodes[node].get('party', 'Unknown') for node in sorted_nodes]
        palette = {
            'Democrat': 'blue',
            'Republican': 'red',
            'Whig': 'green',
            'Federalist': 'purple',
            'Independent': 'orange',
            'Unknown': 'gray'
        }
        node_colors = [palette.get(p, 'gray') for p in parties]
        node_trace.marker.showscale = False
        node_trace.marker.colorbar = None
    elif node_coloring == 'by year of first use':
        years = [G.nodes[node].get('year') for node in sorted_nodes]
        node_colors = [year if year is not None else min([y for y in years if y is not None], default=0) for year in years]
        node_trace.marker.colorscale = 'Viridis'
        node_trace.marker.colorbar.title.text = 'Year of first use'
    else:
        node_colors = node_degrees
        node_trace.marker.colorscale = 'YlGnBu'
        node_trace.marker.colorbar.title.text = 'Node degree'

    node_trace.marker.color = node_colors
    node_trace.text = [f"{node}<br>degree: {degree}" for node, degree in zip(sorted_nodes, node_degrees)]

    fig = go.Figure(data=[edge_trace, node_trace],
                layout=go.Layout(
                    width=850, height=770,
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=8,l=2,r=100,t=50),
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                    )
    return fig




##### Helper functions for graph visualization with PyGraphviz 

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
    year = ix[0]
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
    w  = 1.0 + math.sqrt(0.2*(att.get('doc_freq')-1))
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
   """
   Convert a NetworkX graph with node and edge attributes into a DOT format string for 
   visualization with PyGraphviz.
   Parameters:
   - graph: NetworkX graph with node attributes (e.g., 'term_frq', 'used_in') and edge attributes (e.g., 'weight')
   Returns:
   - dot: A string containing the graph in DOT format
   """

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


########## Streamlit app layout and interactivity

if 'submitted' not in st.session_state:
    st.session_state.submitted = False

st.set_page_config(
    page_title="Inauguration Addresses Dashboard",
    layout="wide"
)

st.markdown(
    """
    <style>
    body {  
        color: #f5f7fb;
    }
    .graph-placeholder {
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 24px;
        padding: 24px;
        min-height: 650px;
    }
    .graph-placeholder h2 {
        margin-top: 0;
        color: #f5f7fb;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

left_column, center_column, right_column = st.columns([3, 10, 3])

with left_column:
    with st.form("data_select"):
        st.markdown("#### Data selection")
        # select year range
        year_range = st.slider(
            "Years",
            min_value=1789,
            max_value=2017,
            value=(1789, 2017),
            step=4,
        )
        # select history period
        history = st.selectbox(
            "History",
            ["None", "Civil War", "WW-1", "WW-2","Great Depression", "Cold War"],
        )
        # select party
        party = st.selectbox(
            "Party",
            ["All", "Democrat", "Republican", "Whig", "Federalist", "Independent"],
        )
        keyword_score = st.text_input("Required keyword score", value="0.14")
        
        st.markdown("#### Graph view")
        node_coloring = st.selectbox(
            "Node coloring",
            ["by party", "by year of first use"],
        )
        node_sizing = st.selectbox(
            "Node sizing",
            ["doc_freq", "term_freq", "degree"],
        )
        node_size_growth = st.selectbox(
            "Node size growth",
            ["proportional", "radix"],
        )
        # select the pygraphviz layout engine
        layout_engine = st.selectbox(
            "Layout engine",
            ["sfdp", "neato", "dot", "fdp", "twopi"],
            index=0,
        )
        show_labels = st.radio("Node label", ["yes", "no"], index=1)

        submit_button = st.form_submit_button(label="Apply filters", on_click=submitted)

with center_column:
    st.markdown("<div><h3>US Presidents' Inauguration Addresses</h3><h4 style='margin:20px;'>Graph-based analysis</h4></div>", unsafe_allow_html=True)
    with st.container(horizontal_alignment="center", width=int(1.5*850), height=1000, border=True):
        if st.session_state.submitted:
            corpus = make_corpus(time=year_range, history=history, party=party)
            tfidf_df = vectorize_corpus(corpus)
            B = create_bipartite_graph(tfidf_df, keyword_score, corpus)
            #st.write(f"Number of nodes in bipartite graph: {B.number_of_nodes()}")
            #st.write(f"Number of edges in bipartite graph: {B.number_of_edges()}")
            G = create_keyword_graph(B)
            #print(G.nodes(data=True))
            #st.write(f"Number of nodes in keyword graph: {G.number_of_nodes()}")
            #st.write(f"Number of edges in keyword graph: {G.number_of_edges()}")
            #st.plotly_chart(viz_graph(G, node_coloring, node_sizing, node_size_growth))
            # Convert graph to dot format
            dot = graphToDot(G)

            B = pgv.AGraph(string=dot)
            B.layout(prog=layout_engine)

            # Render the pygraphviz layout directly as interactive SVG so tooltip attributes work.
            fd, svg_path = tempfile.mkstemp(suffix=".svg")
            os.close(fd)
            try:
                B.draw(svg_path, format="svg")
                with open(svg_path, "r", encoding="utf-8") as f:
                    svg_text = f.read()

                # Give the SVG an ID so svg-pan-zoom can attach to it, and remove fixed width/height.
                svg_text = svg_text.replace('<svg ', '<svg id="graph-svg" preserveAspectRatio="xMidYMid meet" ', 1)
                svg_text = re.sub(r'\s(width|height)="[^"]+"', '', svg_text)

                st.markdown("Hover over nodes to see tooltips if your browser supports it.")
                svg_html = f"""
            <div id='svg-container' style='width:100%; border:1px solid #ddd;'>
            <div style='display:flex; gap:8px; padding:8px; background:#f8f8f8; border-bottom:1px solid #ddd;'>
                <button id='zoom-in' style='padding:6px 12px;'>Zoom +</button>
                <button id='zoom-out' style='padding:6px 12px;'>Zoom -</button>
                <button id='reset-view' style='padding:6px 12px;'>Reset view</button>
                <button id='fit-view' style='padding:6px 12px;'>Fit view</button>
            </div>
            <div id='svg-wrapper' style='width:100%; height:900px; overflow:hidden;'>
                {svg_text}
            </div>
            </div>
            <script src='https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js'></script>
            <script>
            const panZoom = svgPanZoom('#graph-svg', {{
                zoomEnabled: true,
                controlIconsEnabled: true,
                fit: false,
                center: false,
                minZoom: 0.01,
                maxZoom: 10,
                zoomScaleSensitivity: 0.2,
                dblClickZoomEnabled: true,
                mouseWheelZoomEnabled: true,
                preventMouseEventsDefault: true,
            }});

            const svg = document.getElementById('graph-svg');
            const wrapper = document.getElementById('svg-wrapper');
            svg.style.width = '100%';
            svg.style.height = '100%';
            svg.style.display = 'block';

            function fitGraph() {{
                panZoom.resize();
                panZoom.fit();
                panZoom.center();
            }}

            window.addEventListener('load', () => {{
                fitGraph();
                setTimeout(fitGraph, 100);
                setTimeout(fitGraph, 300);
            }});

            document.getElementById('zoom-in').addEventListener('click', () => panZoom.zoomIn());
            document.getElementById('zoom-out').addEventListener('click', () => panZoom.zoomOut());
            document.getElementById('reset-view').addEventListener('click', () => {{ panZoom.resetZoom(); panZoom.resetPan(); panZoom.center(); }});
            document.getElementById('fit-view').addEventListener('click', () => {{ panZoom.fit(); panZoom.center(); }});
            </script>
            """
                
                st.iframe(svg_html, height=950, width=1600)
            finally:
                os.remove(svg_path)



with right_column:
    st.markdown("##### Key graph data")
    if st.session_state.submitted:
        st.write(f"{len(corpus)} inauguration addresses in selection")
        st.write(f"{G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        st.write(f"{nx.number_connected_components(G)} connected components")
        st.write(f"Graph density: {nx.density(G):.4f}")

    st.markdown("##### Top 20 document frequencies")
    if st.session_state.submitted:
        doc_freq_dict = create_doc_freq_dict(tfidf_df, keyword_score)
        top_20 = sorted(doc_freq_dict.items(), key=lambda item: item[1], reverse=True)[:20]
        terms = [k for k, v in top_20]
        freqs = [v for k, v in top_20]
        fig = go.Figure(data=[go.Bar(x=terms, y=freqs)])
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig)
    
    st.markdown("##### Top 20 betweenness values")
    if st.session_state.submitted:
        betweenness = nx.betweenness_centrality(G)
        top_20 = sorted(betweenness.items(), key=lambda item: item[1], reverse=True)[:20]
        nodes = [k for k, v in top_20]
        values = [v for k, v in top_20]
        fig = go.Figure(data=[go.Bar(x=nodes, y=values)])
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig)

    st.markdown("##### Degree distribution")
    if st.session_state.submitted:
        hist = nx.degree_histogram(G)
        degrees = list(range(len(hist)))
        counts = hist
        fig = go.Figure(data=[go.Bar(x=degrees, y=counts)])
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig)

    st.markdown("##### Short comment")
st.markdown("---")

########## Debug & state preview


st.markdown(
    "#### Debug & state preview\n"
    f"**Years:** {year_range}  \n"
    f"**History:** {history}  \n"
    f"**Party:** {party}  \n"
    f"**Node coloring:** {node_coloring}  \n"
    f"**Node sizing:** {node_sizing}  \n"
    f"**Node size growth:** {node_size_growth}  \n"
    f"**Keyword score:** {keyword_score or 'None'}  \n"
    f"**Node labels:** {show_labels}",
)

del st.session_state.submitted