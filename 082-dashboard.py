import os
import itertools
from unittest import result
import pygraphviz as pgv
from bs4 import BeautifulSoup
import spacy
import base64
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
import tempfile
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
    #print (tfidf_df.head())
    return tfidf_df

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
    reduced_df = tfidf_df.where(tfidf_df >= float(keyword_score), other=0) 
    reduced_df.loc['doc_freq'] = reduced_df.mask(reduced_df > 0, 1).sum()
    doc_freq_dict = {k: int(v) for k, v in reduced_df.loc['doc_freq'].to_dict().items()}
    #print(reduced_df[['arrive', 'repose', 'punishment', 'magistrate', 'incur', 'official']])
    return doc_freq_dict

### Create tf-idf dict for each term in graph
def create_tfidf_dict(tfidf_df, keyword_score):
    """
    Create a dictionary mapping each term to its maximum TF-IDF score in the final graph.
    Parameters:
    - tfidf_df: DataFrame with addresses as rows and terms as columns, containing TF-IDF scores
    - keyword_score: float, threshold for keyword relevance
    Returns:
    - tfidf_dict: dict mapping term to TF-IDF score
    """
    reduced_df = tfidf_df.where(tfidf_df >= float(keyword_score), other=0) 
    tfidf_dict = reduced_df.max().to_dict()
    return tfidf_dict

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
    # Reframe the tfidf dataFrame so that the terms are in a single column rather than in a rows
    stacked_df = tfidf_df.stack().reset_index().rename(columns={0:'tfidf', 'level_0': 'address','level_1': 'term'})

    # Set threshold for TF-IDF values and determine remaining terms
    thres_tfidf = stacked_df[stacked_df['tfidf'] >= float(keyword_score)]
    #print (thres_tfidf)

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
    
    # Create document frequency dict for terms
    doc_freq_dict = create_doc_freq_dict(tfidf_df, keyword_score)
    tf_idf_dict = create_tfidf_dict(tfidf_df, keyword_score)
    
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
            B.nodes[node]['doc_freq'] = doc_freq_dict[node]
            B.nodes[node]['term_frq'] = tf_idf_dict[node]
    return B

### Create (address-to-address) address graph from (term-to-address) bipartite graph by projection
def create_address_graph(B):
    """
    Create a keyword graph by projecting the bipartite graph onto the term nodes, 
    where edges between terms indicate co-occurrence in the same address. Additionally,
    set degree attribute for nodes of the keyword graph based on the number of connections in the projected graph.
       Parameters:
       - B: bipartite graph
       Returns:
       - X: address graph
    """
    X = bipartite.weighted_projected_graph(B, [n for n, d in B.nodes(data=True) if d['type'] == 'address'])
    # set degree attribute
    for node in X.nodes():
        if X.nodes[node]['type'] == 'address':
            X.nodes[node]['degree'] = X.degree(node)
    
    # create lists of shared terms for each edge in the address graph and set as edge attribute
    a_nodes = [n for n, d in B.nodes(data=True) if d['type'] == 'address']
    for u, v in itertools.combinations(a_nodes, 2):
        # Schnittmenge aller gemeinsamen Nachbarn bilden
        #print(u,list(B.neighbors(u)))
        shared_terms = set(B.neighbors(u)) & set(B.neighbors(v))
        shared_terms_list = list(shared_terms) if shared_terms else []
        if X.has_edge(u, v):
            X.edges[(u, v)]['common_terms'] = shared_terms_list

    return X

### Create (term-to-term) keyword graph from (term-to-address) bipartite graph by projection
def create_keyword_graph(B):
    """
    Create a keyword graph by projecting the bipartite graph onto the term nodes, 
    where edges between terms indicate co-occurrence in the same address. Additionally,
    set degree attribute for nodes of the keyword graph based on the number of connections in the projected graph.
       Parameters:
       - B: bipartite graph
       Returns:
       - G: keyword graph
    """
    X = bipartite.weighted_projected_graph(B, [n for n, d in B.nodes(data=True) if d['type'] == 'term'])
    # set degree attribute
    for node in X.nodes():
        if X.nodes[node]['type'] == 'term':
            X.nodes[node]['degree'] = X.degree(node)
    return X

##### Helper functions for graph visualization with PyGraphviz 

# Functions to compute node attributes
dark = False
directory_path_in = "./misc/"
with open(f"{directory_path_in}meta.json", 'r', encoding='utf-8') as f:
    meta = json.load(f)
    f.close()
#print(meta)

def computeNodeFillcolor_party(att):
    global dark
    xx = att['party']
    if xx == 'Republican':
        dark = True
        return '#E9141D'
    elif xx == 'Democrat':
        dark = True
        return '#0015BC'
    else:
        return 'lightblue'

def XcomputeNodeFillcolor_party(att):
    global dark
    xx = att['used_in']
    y = [meta[x]['party'] for x in xx]
    z = dict(Counter(y))
    if 'Republican' in z and 'Democrat' in z:
        return 'Thistle'
    elif 'Republican' in z:
        dark = True
        return '#E9141D'
    elif 'Democrat' in z:
        dark = True
        return '#0015BC'
    else:
        return 'lightblue'


def computeNodeFillcolor_year(att):
    global dark
    year = int(att['year'])
    blue2yellow = [('#081d58ff','dark'), ('#253494ff', 'dark'), ('#225ea8ff', 'dark'), ('#1d91c0ff', 'light'), \
                   ('#41b6c4ff', 'light'), ('#7fcdbbff', 'light'), ('#c7e9b4ff', 'light'), ('#edf8b1ff', 'light'), ('#ffffd9ff', 'light')]
    pastell   = [('#fbb4aeff', 'light'), ('#b3cde3ff', 'light'), ('#ccebc5ff', 'light'), ('#decbe4ff', 'light'), \
                 ('#fed9a6ff', 'light'), ('#ffffccff', 'light'), ('#e5d8bdff', 'light'), ('#fddaecff', 'light'), ('#f2f2f2ff', 'light')]
    palette = blue2yellow
    if year == 1789 or year == 1793:  # G. Washington's addresses
        if palette[0][1] == "dark":
            dark = True
        return palette[0][0]
    elif year >  1793 and year < 1805:
        if palette[1][1] == "dark":
            dark = True
        return palette[1][0]
    elif year >= 1805 and year < 1833:
        if palette[2][1] == "dark":
            dark = True
        return palette[2][0]
    elif year >= 1833 and year < 1866:
        if palette[3][1] == "dark":
            dark = True
        return palette[3][0]
    elif year >= 1866 and year < 1905:
        if palette[4][1] == "dark":
            dark = True
        return palette[4][0]
    elif year >= 1905 and year < 1933:
        if palette[5][1] == "dark":
            dark = True
        return palette[5][0]
    elif year >= 1933 and year < 1965:
        if palette[6][1] == "dark":
            dark = True
        return palette[6][0]
    elif year >= 1965 and year < 2001:
        if palette[7][1] == "dark":
            dark = True
        return palette[7][0]
    elif year >= 2001:
        if palette[8][1] == "dark":
            dark = True
        return palette[8][0]
    else:
        return 'lightblue'
    
def computeNodeFillcolor(att, node_coloring):
    if node_coloring == "by party":
        return computeNodeFillcolor_party(att)
    elif node_coloring == "by year of first use":
        return computeNodeFillcolor_year(att)
    else:
        return 'lightblue'

def computeNodeWidth(att, node_sizing, node_size_growth):
    if att['type'] == 'address':
        if node_size_growth == "proportional":
            w = max(64, 8.0*int(att.get('degree')))
        elif node_size_growth == "radix":
            w = max(64, 32.0*math.sqrt(int(att.get('degree'))))
        else:
            st.error("Invalid node size growth option selected.")
    elif att['type'] == 'term':
        if node_sizing == "doc_freq":
            if node_size_growth == "proportional":
                w = max(48, 8.0*int(att.get('doc_freq')))
            elif node_size_growth == "radix":
                w = max(48, 32.0*math.sqrt((att.get('doc_freq'))))
            else:
                st.error("Invalid node size growth option selected.")
        elif node_sizing == "degree":
            if node_size_growth == "proportional":
                w = max(64, 8.0*int(att.get('degree')))
            elif node_size_growth == "radix":
                w = max(64, 32.0*math.sqrt(int(att.get('degree'))))
            else:
                st.error("Invalid node size growth option selected.")
        elif node_sizing == "tf-idf":
            if node_size_growth == "proportional":
                w = max(48, 8.0*att.get('term_frq'))
            elif node_size_growth == "radix":
                w = max(48, 32.0*math.sqrt((att.get('term_frq'))))
        else:
            st.error("Invalid node sizing option selected.")
    else:
        st.error("Invalid node type.")
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
    return str(max(4, 16*att.get('weight'))) 

def computeEdgeColor(att):
    if att.get('weight') > 1:
        return 'SlateGray'
    else:
        return 'black'

def computeEdgeTooltip(att):
    xx = str(att['common_terms'])
    return xx.replace("[", "").replace("]", "").replace(", ", "\n") 

def graphToDot(graph=None, node_coloring="by year of first use", node_sizing="doc_freq", node_size_growth="proportional"):
   """
   Convert a NetworkX graph with node and edge attributes into a DOT format string for visualization with PyGraphviz.
   Parameters:
   - graph: NetworkX graph with node attributes (e.g., 'term_frq', 'used_in') and edge attributes (e.g., 'weight')
   Returns:
   - dot: A string containing the graph in DOT format
   """

   #dot file header
   dot  = 'graph {\n   overlap="prism1000" rankdir="LR" outputorder="edgesfirst" splines="false" bgcolor="silver" fontsize="60" fontname="Arial" labelloc="t" labeljust="l"\n'
   dot += '   node [margin=0 fontname="Arial" fontcolor="black" shape=circle style=filled fixedsize=true];\n'
   # edges
   for u,v,att in graph.edges(data=True):
      dot += f'   "{u}" -- "{v}" [id="{u}--{v}"'
      dot += f' penwidth={computeEdgePenwidth(att)}, tooltip="{computeEdgeTooltip(att)}"]\n'
      #dot += f' color="{computeEdgeColor(att)}"]\n'
   #nodes
   for u,att in graph.nodes(data=True):
      # set two part label for address nodes, and single part label for term nodes
      lbl = u.split("_")[0] + "_" + u.split("_")[-1] if att['type'] == 'address' else u
      dot += f'   "{u}" [id="{u}", label="{lbl}", '
      wdth = computeNodeWidth(att, node_sizing, node_size_growth)
      dot += f' width={wdth}, fontsize={max(64, wdth*12)}, '
      dot += f' fillcolor="{computeNodeFillcolor(att, node_coloring)}"'  
      dot += f' fontcolor="{computeNodeFontcolor()}"]\n' 
      #dot += f' tooltip="{computeNodeTooltip(att)}"]\n'
   # close dot string
   dot += '}'
   #print(dot)
   return dot

########## Streamlit app layout and interactivity

if 'submitted' not in st.session_state:
    st.session_state.submitted = False

st.set_page_config(
    page_title="Inauguration Addresses Dashboard",
    layout="wide"
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
            index=0,
        )
        # select party
        party = st.selectbox(
            "Party",
            ["All", "Democrat", "Republican", "Whig", "Federalist", "Independent"],
            index=0,
        )

        st.markdown("#### Graph construction")

        # select type of graph
        graph_type = st.radio("Type of graph", options=["Keyword graph", "Address graph"], horizontal=True, index=0)

        # select keyword score threshold
        keyword_score = st.slider(
            "Keyword score",
            min_value=0.05,
            max_value=0.5,
            value=0.14,
            step=0.01,
        )

        st.markdown("#### Graph visualization")

        # select node coloring
        node_coloring = st.selectbox(
            "Node coloring",
            ["by year of first use", "by party"],
            index=0,
        )
        # select node sizing
        node_sizing = st.selectbox(
            "Node sizing",
            ["doc_freq", "degree", "tf-idf"],
            index=0,
        )
        # select algorithm for node size growth
        node_size_growth = st.selectbox(
            "Node size growth",
            ["radix", "proportional"],
            index=0,
        )
        # select the pygraphviz layout engine
        layout_engine = st.selectbox(
            "Layout engine",
            ["sfdp", "neato", "dot", "fdp", "twopi"],
            index=0,
        )

        submit_button = st.form_submit_button(label="Apply filters", on_click=submitted)

with center_column:
    st.markdown("<div><h3>US Presidents' Inauguration Addresses</h3><h4 style='margin:20px;'>Graph-based analysis</h4></div>", unsafe_allow_html=True)
    
    if st.session_state.submitted:
        corpus = make_corpus(time=year_range, history=history, party=party)
        tfidf_df = vectorize_corpus(corpus)
        B = create_bipartite_graph(tfidf_df, keyword_score, corpus)
        if graph_type == "Address graph":
            G = create_address_graph(B)
            print(G.nodes(data=True))
            print(G.edges(data=True))
        elif graph_type == "Keyword graph":
            G = create_keyword_graph(B)
        else:
            st.error("Invalid graph type selected.")
        
        # Convert graph to dot format
        dot = graphToDot(G, node_coloring, node_sizing, node_size_growth)
        X = pgv.AGraph(string=dot)
        X.layout(prog=layout_engine)

        # create temp file and write the pygraphviz layout to temp file in SVG format
        fd, svg_path = tempfile.mkstemp(suffix=".svg")
        X.draw(svg_path, format="svg")
        os.close(fd)

        # read the SVG file back as a string for embedding it into the HTML template
        with open(svg_path, "r", encoding="utf-8") as f:
            graphviz_svg_output = f.read()

        # create the HTML template with embedded SVG and JavaScript for interactivity (pan, zoom, focus mode, download)
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                html, body {{
                    margin: 0; padding: 0; width: 100%; height: 100%; 
                    overflow: hidden; background-color: silver; font-family: sans-serif;
                }}
                .container {{ position: relative; width: 100%; height: 100%; background-color: silver; }}
                svg {{ width: 100% !important; height: 100% !important; cursor: move; user-select: none; }}
                
                /* Steuerungs-Leiste oben links */
                .controls {{
                    position: absolute; top: 15px; left: 15px; 
                    display: flex; gap: 10px; z-index: 10;
                }}
                .btn {{
                    padding: 8px 14px; background-color: #ffffff; color: #31333F; 
                    border: 1px solid #d3d3d3; border-radius: 8px; cursor: pointer; 
                    font-size: 14px; font-weight: 500; box-shadow: 0px 2px 4px rgba(0,0,0,0.1);
                    display: flex; align-items: center; gap: 6px; transition: background-color 0.2s;
                }}
                .btn:hover {{ background-color: #f0f2f6; }}

                /* Fokus & Overlay Styles (unverändert) */
                svg.fokus-aktiv .node, svg.fokus-aktiv .edge {{ opacity: 0.15; transition: opacity 0.3s ease; }}
                svg.fokus-aktiv .node.highlight-target,
                svg.fokus-aktiv .node.highlight-neighbor,
                svg.fokus-aktiv .edge.highlight-connected {{ opacity: 1 !important; }}
                .node {{ cursor: pointer; }}
                .node:hover {{ filter: brightness(0.9); }}
            </style>
        </head>
        <body>

        <div class="container" id="iframe-container">
            <!-- Flex-Leiste für beide Buttons -->
            <div class="controls">
                <button id="reset-btn" class="btn">Reset view</button>
                <button id="download-btn" class="btn">Download SVG</button>
            </div>
            {graphviz_svg_output}
        </div>

        <script>
            window.onload = function() {{
                const svg = document.querySelector('svg');
                const resetBtn = document.getElementById('reset-btn');
                const downloadBtn = document.getElementById('download-btn');
                if (!svg) return;

                svg.setAttribute('preserveAspectRatio', 'xMidYMin meet');

                const baseVB = svg.viewBox.baseVal;
                const defaultVB = {{ x: baseVB.x, y: baseVB.y, width: baseVB.width, height: baseVB.height }};
                let currentVB = {{ ...defaultVB }};
                let isPanning = false;
                let startPoint = {{ x: 0, y: 0 }};

                function applyViewBox() {{
                    svg.setAttribute('viewBox', `${{currentVB.x}} ${{currentVB.y}} ${{currentVB.width}} ${{currentVB.height}}`);
                }}

                applyViewBox();

                // --- DOWNLOAD LOGIK ---
                downloadBtn.addEventListener('click', function() {{
                    // 1. Erstelle eine exakte Textkopie des aktuellen SVG-Elements aus dem DOM
                    const serializer = new XMLSerializer();
                    const svgCopy = svg.cloneNode(true);

                    const bgPolygon = svgCopy.querySelector('polygon[fill="silver"]');
                    bgPolygon.setAttribute('fill', 'none');
                    // Falls zusätzlich Inline-Styles gesetzt sind, diese auch überschreiben
                    bgPolygon.style.fill = 'none';
                    let svgString = serializer.serializeToString(svgCopy);
                    
                    // 2. XML-Standardheader hinzufügen für maximale Kompatibilität in Illustrator/Inkscape
                    svgString = '<?xml version="1.0" standalone="no"?>\\n' + svgString;
                    
                    // 3. Textdaten in ein Blob-Objekt konvertieren (MIME-Type: image/svg+xml)
                    const blob = new Blob([svgString], {{ type: 'image/svg+xml;charset=utf-8' }});
                    const blobUrl = URL.createObjectURL(blob);
                    
                    // 4. Temporären Download-Link im Browser simulieren und auslösen
                    const downloadLink = document.createElement('a');
                    downloadLink.href = blobUrl;
                    downloadLink.download = 'graphviz_dashboard.svg'; // Dateiname
                    document.body.appendChild(downloadLink);
                    downloadLink.click();
                    
                    // 5. Speicherbereinigung
                    document.body.removeChild(downloadLink);
                    URL.revokeObjectURL(blobUrl);
                }});

                // --- FOKUS-MODUS (KLICK-LOGIK) ---
                const nodes = svg.querySelectorAll('.node');
                const edges = svg.querySelectorAll('.edge');

                nodes.forEach(node => {{
                    node.addEventListener('click', function(e) {{
                        e.stopPropagation();
                        const titleEl = node.querySelector('title');
                        if (!titleEl) return;
                        const nodeName = titleEl.textContent.trim();

                        svg.classList.add('fokus-aktiv');
                        nodes.forEach(n => n.classList.remove('highlight-target', 'highlight-neighbor'));
                        edges.forEach(edge => edge.classList.remove('highlight-connected'));
                        node.classList.add('highlight-target');

                        edges.forEach(edge => {{
                            const edgeTitleEl = edge.querySelector('title');
                            if (edgeTitleEl) {{
                                const edgeText = edgeTitleEl.textContent.trim();
                                if (edgeText.startsWith(nodeName + '->') || edgeText.endsWith('->' + nodeName) || 
                                    edgeText.includes('--' + nodeName) || edgeText.includes(nodeName + '--')) {{
                                    edge.classList.add('highlight-connected');
                                    const parts = edgeText.split(/->|--/);
                                    const neighborName = parts[0].trim() === nodeName ? parts[1].trim() : parts[0].trim();
                                    nodes.forEach(n => {{
                                        const nTitle = n.querySelector('title');
                                        if (nTitle && nTitle.textContent.trim() === neighborName) {{
                                            n.classList.add('highlight-neighbor');
                                        }}
                                    }});
                                }}
                            }}
                        }});
                    }});
                }});

                svg.addEventListener('click', function() {{
                    svg.classList.remove('fokus-aktiv');
                    nodes.forEach(n => n.classList.remove('highlight-target', 'highlight-neighbor'));
                    edges.forEach(edge => edge.classList.remove('highlight-connected'));
                }});

                // --- RE-ZENTRIERUNG BEI FENSTER-RESIZE ---
                let lastWidth = window.innerWidth;
                let lastHeight = window.innerHeight;
                window.addEventListener('resize', () => {{
                    if (window.innerWidth === 0 || window.innerHeight === 0) return;
                    const dx = window.innerWidth - lastWidth; const dy = window.innerHeight - lastHeight;
                    currentVB.width += dx * (currentVB.width / window.innerWidth);
                    currentVB.height += dy * (currentVB.height / window.innerHeight);
                    lastWidth = window.innerWidth; lastHeight = window.innerHeight; applyViewBox();
                }});

                resetBtn.addEventListener('click', function() {{
                    currentVB = {{ ...defaultVB }}; applyViewBox();
                    svg.classList.remove('fokus-aktiv');
                }});

                // --- MAUS-INTERAKTIONEN (PAN & ZOOM) ---
                svg.addEventListener('mousedown', function(e) {{
                    e.preventDefault(); isPanning = true; startPoint = {{ x: e.clientX, y: e.clientY }};
                }});

                svg.addEventListener('mousemove', function(e) {{
                    if (!isPanning) return;
                    const rect = svg.getBoundingClientRect();
                    const dx = (e.clientX - startPoint.x) * (currentVB.width / rect.width);
                    const dy = (e.clientY - startPoint.y) * (currentVB.height / rect.height);
                    currentVB.x -= dx; currentVB.y -= dy;
                    startPoint = {{ x: e.clientX, y: e.clientY }}; applyViewBox();
                }});

                window.addEventListener('mouseup', function() {{ isPanning = false; }});

                svg.addEventListener('wheel', function(e) {{
                    e.preventDefault(); const rect = svg.getBoundingClientRect();
                    const mouseXRatio = (e.clientX - rect.left) / rect.width;
                    const mouseYRatio = (e.clientY - rect.top) / rect.height;
                    const zoomFactor = e.deltaY < 0 ? 0.88 : 1.12;
                    const newWidth = currentVB.width * zoomFactor; const newHeight = currentVB.height * zoomFactor;
                    currentVB.x += (currentVB.width - newWidth) * mouseXRatio;
                    currentVB.y += (currentVB.height - newHeight) * mouseYRatio;
                    currentVB.width = newWidth; currentVB.height = newHeight; applyViewBox();
                }}, {{ passive: false }});
            }};
        </script>
        </body>
        </html>
        """

        # Encode the HTML template as base64 to create a data URI for embedding in the iframe
        b64_html = base64.b64encode(html_template.encode("utf-8")).decode("utf-8")
        src_data_uri = f"data:text/html;base64,{b64_html}"

        st.iframe(
            src=src_data_uri,
            width="stretch",
            height=2400
        )

        # close and delete the temporary SVG file after reading its content
        f.close()
        os.remove(svg_path)

with right_column:
    st.markdown("##### Key graph metrics")
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

del st.session_state.submitted