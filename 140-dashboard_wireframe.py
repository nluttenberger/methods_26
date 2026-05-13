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

    # Reframe the tfidf dataFrame so that the terms are in rows rather than columns.
    stacked_df = tfidf_df.stack().reset_index().rename(columns={0:'tfidf', 'level_0': 'address','level_1': 'term'})
    return stacked_df

### Create bipartite graph from stacked tf-idf DataFrame
def create_bipartite_graph(stacked_df, keyword_score):
    """
    Create a bipartite graph where one set of nodes represents addresses and the other set represents terms, 
    with edges indicating the presence of a term in an address based on the thresholded TF-IDF values.
    Parameters:
    - stacked_df: DataFrame with columns 'address', 'term', and 'tfidf'
    - keyword_score: float, threshold for keyword relevance
    Returns:
    - B: bipartite graph
    """
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
    return B

### Create document frequency dict
def create_doc_freq_dict(stacked_df, keyword_score):
    """
    Create a dictionary mapping each term to its document frequency (number of addresses it appears in).
    Parameters:
    - stacked_df: DataFrame with columns 'address', 'term', and 'tfidf'
    - keyword_score: float, threshold for keyword relevance
    Returns:
    - doc_freq_dict: dict mapping term to document frequency
    """
    doc_freq_dict = stacked_df['term'].value_counts().to_dict()
    print(f"Created document frequency dictionary:\n {doc_freq_dict} ")
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
    return bipartite.weighted_projected_graph(B, [n for n, d in B.nodes(data=True) if d['type'] == 'term'])

def x_create_keyword_graph():
    # Reconstruct the graph
    with open('graphs/USPresInaugAddr_0.14.json', 'r', encoding='utf-8') as f:
        InaugAddr_json = json.load(f)
    G = nx.node_link_graph(InaugAddr_json)
    print(G)
    return G

### Graph visualization function using Plotly and NetworkX
def viz_graph(G=None):
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
            size=10,
            colorbar=dict(
                thickness=15,
                title=dict(
                text='Node degree',
                side='right'
                ),
                xanchor='left',
            ),
            line_width=0.5))

    node_trace.marker.color = node_degrees
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

########## Streamlit app layout and interactivity

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
    .dashboard-card {
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 16px;
        padding: 18px;
        margin-bottom: 16px;
        min-height: 130px;
    }
    .dashboard-card h3 {
        margin: 0 0 12px 0;
        font-size: 1rem;
        color: black;
    }
    .dashboard-card p {
        margin: 0;
        color: black;
        opacity: .86;
        line-height: 1.6;
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
        year_range = st.slider(
            "Years",
            min_value=1789,
            max_value=2017,
            value=(1789, 2017),
            step=4,
        )
        history = st.selectbox(
            "History",
            ["None", "Civil War", "WW-1", "WW-2","Great Depression", "Cold War"],
        )
        party = st.selectbox(
            "Party",
            ["All", "Demokrat", "Republikaner", "Whig", "Federalist", "Independent"],
        )
        
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
        keyword_score = st.text_input("Required keyword score", value="0.14")
        show_labels = st.radio("Node label", ["yes", "no"], index=1)

        submit_button = st.form_submit_button(label="Apply filters")

with center_column:
    st.markdown("<div><h3>US Presidents' Inauguration Addresses</h3><h4 style='margin:20px;'>Graph-based analysis</h4></div>", unsafe_allow_html=True)
    with st.container(horizontal_alignment="center", width=int(1.5*850), height=1000, border=True):
        G = x_create_keyword_graph()
        st.plotly_chart(viz_graph(G))

with right_column:
    st.markdown("<div class='dashboard-card'><h3>key graph data</h3><p>Summary details for the selected graph, number of nodes, edges, and filters used.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='dashboard-card'><h3>degree distribution in selection</h3><p>Histogram or aggregated distribution metrics for node degrees in the current selection.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='dashboard-card'><h3>doc. freq. distribution in selection</h3><p>Document frequency distribution over the filtered address selection.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='dashboard-card'><h3>term freq. distribution in selection</h3><p>Term frequency distribution showing how often keywords appear in the selected corpus.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='dashboard-card'><h3>short text excerpts</h3><p>Short excerpt or observation related to the current filter and graph view.</p></div>", unsafe_allow_html=True)

st.markdown("---")

########## Debug & state preview
if submit_button:
    corpus = make_corpus(time=year_range, history=history, party=party)
    st.write(f"Number of texts found: {len(corpus)}")
    stacked_df = vectorize_corpus(corpus)
    B = create_bipartite_graph(stacked_df, keyword_score=keyword_score)
    st.write(f"Number of nodes in bipartite graph: {B.number_of_nodes()}")
    st.write(f"Number of edges in bipartite graph: {B.number_of_edges()}")
    G = create_keyword_graph(B)
    st.write(f"Number of nodes in keyword graph: {G.number_of_nodes()}")
    st.write(f"Number of edges in keyword graph: {G.number_of_edges()}")
    print(create_doc_freq_dict(stacked_df, keyword_score))

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