import streamlit as st
import requests
from streamlit_pdf_viewer import pdf_viewer
import io
from pypdf import PdfReader
from streamlit_keypress import key_press_events

st.title("Some slides")
st.write("from my presentation at the KIT \"Bundestagsreden-Seminar\" in June 2026\n\n")
st.write("Use the left and right arrow keys to navigate through the slides.")

# Verwende die direkte Raw-Download-URL von GitHub
pdf_url = "https://raw.githubusercontent.com/nluttenberger/methods_26/local/Dashboard%2007.pdf"

@st.cache_data
def load_pdf(url):
    response = requests.get(url)
    response.raise_for_status()
    pdf_file = io.BytesIO(response.content)
    reader = PdfReader(pdf_file)
    total_pages = len(reader.pages)
    return response, total_pages

# 1. PDF laden und Gesamtseitenzahl ermitteln
response, total_pages = load_pdf(pdf_url)

# 2. Aktuelle Seite im Session State speichern (Standard: Seite 1)
if "current_page" not in st.session_state:
    st.session_state.current_page = 1

# 3. Unsichtbarer Key-Listener wird aktiviert
key = key_press_events()
if key:
    if key == "ArrowRight" and st.session_state.current_page < total_pages:
        st.session_state.current_page += 1
    elif key == "ArrowLeft" and st.session_state.current_page > 1:
        st.session_state.current_page -= 1

# 4. Aktuelle Seite rendern
pdf_viewer(
    input=response.content,
    width=1600,
    pages_to_render=[st.session_state.current_page]  # Übergibt die aktuelle Seite als Liste
)
