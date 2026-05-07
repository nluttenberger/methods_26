import streamlit as st

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

left_column, center_column, right_column = st.columns([2, 8, 4])

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
        party = st.selectbox(
            "Party",
            ["All", "Democrat", "Republican", "Whig", "Federalist", "Independent"],
        )
        history = st.selectbox(
            "History",
            ["All", "Civil War", "WWI", "Great Depression", "Cold War"],
        )

        st.markdown("#### Graph construction")
        node_coloring = st.selectbox(
            "Node coloring",
            ["by party", "by year of first use"],
        )
        node_sizing = st.selectbox(
            "Node sizing",
            ["proportional", "radix"],
        )
        keyword_score = st.text_input("Required keyword score")

        st.markdown("#### View")
        keyword_select = st.text_input("Select single keyword")

        show_labels = st.radio("Node label", ["yes", "no"], index=1)

        submit_button = st.form_submit_button(label="Apply filters")


with center_column:

    st.markdown("<div class='title-block'><h1>US Presidents' Inauguration Addresses</h1><h4 style='margin:20px;'>Graph-based analysis</h4></div>", unsafe_allow_html=True)
    with st.container(horizontal_alignment="center", vertical_alignment="top"):
        st.image("graphs/USPresInaugAddr_0.14.bokeh.svg")

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
    f"**Party:** {party}  \n"
    f"**History:** {history}  \n"
    f"**Node coloring:** {node_coloring}  \n"
    f"**Node sizing:** {node_sizing}  \n"
    f"**Keyword score:** {keyword_score or 'None'}  \n"
    f"**Single keyword:** {keyword_select or 'None'}  \n"
    f"**Node labels:** {show_labels}",
)
