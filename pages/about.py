import streamlit as st

st.set_page_config(layout="wide")
left_column, center_column, right_column = st.columns([3, 10, 3])

with center_column:
    st.title("About the US Presidential Addresses")
    st.write("The U.S. presidential inauguration addresses are historic speeches delivered by incoming presidents to unify the nation, outline their administration's vision, and address current crises.") 
    st.write("Since 1789, these 63 addresses have evolved from indoor speeches to major outdoor events at the Capitol.")
    st.markdown("""- George Washington (1793): Shortest address at only 135 words.""")
    st.markdown("""- William Henry Harrison (1841): Longest address at 8,455 words, lasting nearly two hours.""")
    st.markdown("""- Abraham Lincoln (1861/1865): Focused on avoiding war and later, reconciling the nation with "malice toward none; with charity for all".""")
    st.markdown("""- Franklin D. Roosevelt (1933): Famously declared during the Great Depression that "the only thing we have to fear is fear itself".""")
    st.markdown("""- John F. Kennedy (1961): Challenged citizens with "ask not what your country can do for you—ask what you can do for your country".""")
    st.markdown("""- Ronald Reagan (1981): Declared that "government is not the solution to our problem; government is the problem".""")
    st.write("In this project, we're using a subset of 58 addresses, held between 1789 and 2017.")
    st.title("About this project")
    st.title("About me")