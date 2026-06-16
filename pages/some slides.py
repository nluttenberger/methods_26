import io
import os
import streamlit as st
from pypdf import PdfReader
from streamlit_keypress import key_press_events
from streamlit_pdf_viewer import pdf_viewer

# Seitenlayout auf Wide-Mode stellen, damit Platz für die seitlichen Buttons ist
st.set_page_config(layout="wide")

st.title("Some slides")
st.write(
    'from my presentation at the KIT "Bundestagsreden-Seminar" in June 2026\n\n'
)
st.write(
    "Use the left and right arrow keys on your PC or the triangle buttons on your tablet to navigate."
)

# 1. DATEINAME DEFINIEREN (Lokal & Cloud-kompatibel)
pdf_filename = "Dashboard 07.pdf"


@st.cache_data(show_spinner=False)
def load_pdf_file(filename):
    with open(filename, "rb") as f:
        pdf_bytes = f.read()
    pdf_file = io.BytesIO(pdf_bytes)
    reader = PdfReader(pdf_file)
    total_pages = len(reader.pages)
    return pdf_bytes, total_pages


if os.path.exists(pdf_filename):
    pdf_bytes, total_pages = load_pdf_file(pdf_filename)
else:
    st.error(
        f"⚠️ Datei '{pdf_filename}' nicht gefunden! Bitte in den app.py-Ordner legen."
    )
    st.stop()

# 2. AKTULLE SEITE INITIALISIEREN
if "current_page" not in st.session_state:
    st.session_state.current_page = 1


# Navigations-Logikfunktionen
def next_page():
    if st.session_state.current_page < total_pages:
        st.session_state.current_page += 1


def prev_page():
    if st.session_state.current_page > 1:
        st.session_state.current_page -= 1


# 3. TASTATUR-STEUERUNG (PC-Kanal via key_press_events)
key = key_press_events()
if key == "ArrowRight":
    next_page()
elif key == "ArrowLeft":
    prev_page()

# --- CSS FÜR GROSSE DREIECKIGE NAVIGATIONBUTTONS ---
st.markdown(
    """
    <style>
        /* Macht die Buttons groß, zentriert und passt sie an Präsentationen an */
        div[data-testid="stColumn"] button {
            width: 100% !important;
            height: 400px !important; /* Große Touch-Fläche fürs Tablet */
            font-size: 40px !important; /* Macht die Dreiecke riesig */
            background-color: rgba(240, 242, 246, 0.6) !important;
            border-radius: 10px !important;
            border: 1px solid #ccc !important;
            transition: background 0.3s;
        }
        div[data-testid="stColumn"] button:active {
            background-color: #e0e0e0 !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# 4. LAYOUT: DREI SPALTEN (Button links | PDF Mitte | Button rechts)
# Proportionale Aufteilung: 1 Teil links, 10 Teile Mitte, 1 Teil rechts
col_left, col_pdf, col_right = st.columns([1, 10, 1])

with col_left:
    # Zurück-Button (Linkes Dreieck)
    st.write(
        "<div style='height: 100px;'></div>", unsafe_allow_html=True
    )  # Schiebt den Button etwas nach unten
    if st.button("◀", key="btn_prev_tablet"):
        prev_page()

with col_pdf:
    # PDF in der Mitte rendern (Breite leicht reduziert für die Spalten)
    pdf_viewer(
        input=pdf_bytes,
        width=1000,
        pages_to_render=[st.session_state.current_page],
    )

with col_right:
    # Vorwärts-Button (Rechtes Dreieck)
    st.write("<div style='height: 100px;'></div>", unsafe_allow_html=True)
    if st.button("▶", key="btn_next_tablet"):
        next_page()

# Seitenzahlanzeige ganz unten zur Kontrolle
st.caption(f"Folie {st.session_state.current_page} von {total_pages}")
