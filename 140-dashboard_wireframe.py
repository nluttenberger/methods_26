
import streamlit as st
import plotly.figure_factory as ff
from numpy.random import default_rng as rng
import plotly.graph_objects as go
import networkx as nx

















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
    .title-block {
        padding: 12px;
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
    .graph-placeholder p {
        color: #cfd8ff;
        opacity: 0.8;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

left_column, center_column, right_column = st.columns([2, 10, 4])

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
            ["All", "Democrat", "Republican", "Whig", "Federalist", "Independent"],
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

    st.markdown("<div class='title-block'><h1>US Presidents' Inauguration Addresses</h1><h4 style='margin:20px;'>Graph-based analysis</h4></div>", unsafe_allow_html=True)
    with st.container(horizontal_alignment="center", vertical_alignment="top", width="stretch"):
        G = nx.random_geometric_graph(200, 0.125)
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = G.nodes[edge[0]]['pos']
            x1, y1 = G.nodes[edge[1]]['pos']
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

        node_x = []
        node_y = []
        for node in G.nodes():
            x, y = G.nodes[node]['pos']
            node_x.append(x)
            node_y.append(y)

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
                reversescale=True,
                color=[],
                size=10,
                colorbar=dict(
                    thickness=15,
                    title=dict(
                    text='Node Connections',
                    side='right'
                    ),
                    xanchor='left',
                ),
                line_width=2))
        fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        title=dict(
                            text="<br>Network graph made with Python",
                            font=dict(
                                size=16
                            )
                        ),
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=20,l=5,r=5,t=40),
                        annotations=[ dict(
                            text="Python code: <a href='https://plotly.com/python/network-graphs/'> https://plotly.com/python/network-graphs/</a>",
                            showarrow=False,
                            xref="paper", yref="paper",
                            x=0.005, y=-0.002 ) ],
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
                        )
        st.plotly_chart(fig)

with right_column:

    st.markdown("<div class='dashboard-card'><h3>key graph data</h3><p>Summary details for the selected graph, number of nodes, edges, and filters used.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='dashboard-card'><h3>degree distribution in selection</h3><p>Histogram or aggregated distribution metrics for node degrees in the current selection.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='dashboard-card'><h3>doc. freq. distribution in selection</h3><p>Document frequency distribution over the filtered address selection.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='dashboard-card'><h3>term freq. distribution in selection</h3><p>Term frequency distribution showing how often keywords appear in the selected corpus.</p></div>", unsafe_allow_html=True)
    st.markdown("<div class='dashboard-card'><h3>short text</h3><p>Short excerpt or observation related to the current filter and graph view.</p></div>", unsafe_allow_html=True)

st.markdown("---")
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
