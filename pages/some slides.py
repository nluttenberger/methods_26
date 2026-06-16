import io
import os
import streamlit as st
from pypdf import PdfReader
from streamlit_keypress import key_press_events
from streamlit_pdf_viewer import pdf_viewer

# 1. SEITEN-KONFIGURATION (Wide-Mode schöpft die volle Displaybreite aus)
st.set_page_config(layout="wide")

st.title("Some slides")
st.write(
    'from my presentation at the KIT "Bundestagsreden-Seminar" in June 2026\n\n'
)
st.write(
    "Use the arrow keys on your PC or the triangle buttons on your tablet to navigate."
)

# 2. DATEINAME DEFINIEREN (Lokal & Cloud-kompatibel)
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

# 3. AKTULLE SEITE INITIALISIEREN
if "current_page" not in st.session_state:
    st.session_state.current_page = 1


# Navigations-Logikfunktionen (Aktualisieren NUR den Session State)
def next_page():
    if st.session_state.current_page < total_pages:
        st.session_state.current_page += 1


def prev_page():
    if st.session_state.current_page > 1:
        st.session_state.current_page -= 1


# 4. TASTATUR-STEUERUNG (PC-Kanal)
key = key_press_events()
if "last_key" not in st.session_state:
    st.session_state.last_key = None

# Nur reagieren, wenn eine NEUE Taste gedrückt wurde (verhindert Loops)
if key and key != st.session_state.last_key:
    st.session_state.last_key = key
    if key == "ArrowRight":
        next_page()
    elif key == "ArrowLeft":
        prev_page()
elif not key:
    st.session_state.last_key = None


# --- CSS FÜR RESPONSIVE TOUCH-BUTTONS ---
st.markdown(
    """
    <style>
        /* Blockiert unnötige Ränder des Streamlit-Hauptcontainers für maximale Fläche */
        .block-container {
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
        /* Maximiert die Buttons an den Seitenrändern */
        div[data-testid="stColumn"] button {
            width: 100% !important;
            height: 600px !important; /* Riesige, intuitive Touch-Fläche fürs Tablet */
            font-size: 45px !important;
            background-color: rgba(240, 242, 246, 0.6) !important;
            border-radius: 12px !important;
            border: 1px solid #ddd !important;
        }
        div[data-testid="stColumn"] button:active {
            background-color: #d0d2d6 !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# 5. DYNAMISCHES SPALTEN-LAYOUT
# Proportionale Gewichtung: 1 Teil links, 14 Teile Mitte (PDF), 1 Teil rechts
col_left, col_pdf, col_right = st.columns([1, 14, 1])

with col_left:
    st.write("<div style='height: 180px;'></div>", unsafe_allow_html=True)
    # Zurück-Button (on_click ändert den State sicher vor dem Rendering)
    if st.button("◀", key="btn_prev_tablet", on_click=prev_page):
        pass

with col_pdf:
    # WICHTIG: width=None entfernt das starre Pixelmaß!
    # Das PDF dehnt sich nun automatisch exakt bis zum Rand aus.
    pdf_viewer(
        input=pdf_bytes,
        width=None,
        pages_to_render=[st.session_state.current_page],
        key=f"pdf_viewer_page_{st.session_state.current_page}",
    )

with col_right:
    st.write("<div style='height: 180px;'></div>", unsafe_allow_html=True)
    # Vorwärts-Button
    if st.button("▶", key="btn_next_tablet", on_click=next_page):
        pass

# Seitenzahlanzeige zur zentrierten Kontrolle unter den Slides
st.markdown(
    f"<h3 style='text-align: center; color: gray; margin-top: 20px;'>Folie {st.session_state.current_page} von {total_pages}</h3>",
    unsafe_allow_html=True,
)
