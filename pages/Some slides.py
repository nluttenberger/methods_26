import streamlit as st
from pypdf import PdfReader
from streamlit_pdf_viewer import pdf_viewer
# Importiert den unsichtbaren Key-Listener
from streamlit_keypress import key_press_events

st.title("Some slides")
st.write("from my presentation at the KIT \"Bundestagsreden-Seminar\" in June 2026")

pdf_path = "Dashboard 07.pdf"

# 1. Gesamte Seitenzahl der PDF ermitteln
@st.cache_data
def get_pdf_page_count(path):
    reader = PdfReader(path)
    return len(reader.pages)

total_pages = get_pdf_page_count(pdf_path)

# 2. Aktuelle Seite im Session State speichern (Standard: Seite 1)
if "current_page" not in st.session_state:
    st.session_state.current_page = 1

# Unsichtbarer Key-Listener wird aktiviert
# Er reagiert sofort, wenn eine Taste gedrückt wird
key = key_press_events()

if key:
    if key == "ArrowRight" and st.session_state.current_page < total_pages:
        st.session_state.current_page += 1
    elif key == "ArrowLeft" and st.session_state.current_page > 1:
        st.session_state.current_page -= 1

# 4. PDF einlesen und nur die ausgewählte Seite rendern
with open(pdf_path, "rb") as f:
    binary_data = f.read()

pdf_viewer(
    input=binary_data,
    width=1600,
    pages_to_render=[st.session_state.current_page]  # Übergibt die aktuelle Seite als Liste
)
