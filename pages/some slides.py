import io
import os
import streamlit as st
from pypdf import PdfReader
from streamlit_keypress import key_press_events
from streamlit_pdf_viewer import pdf_viewer

st.title("Some slides")
st.write(
    'from my presentation at the KIT "Bundestagsreden-Seminar" in June 2026\n\n'
)
st.write(
    "Use Arrow keys on PC or Tap/Swipe Left and Right sides of the slide on Tablets."
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

# --- DESIGN FÜR INVISIBLE TOUCH OVERLAYS (CSS) ---
# Dieser CSS-Code legt zwei unsichtbare, riesige Klickflächen über die App
st.markdown(
    """
    <style>
        /* Container für die unsichtbaren Buttons */
        .touch-container {
            position: fixed;
            top: 25%;
            left: 0;
            width: 100vw;
            height: 65vh;
            z-index: 99999; /* Liegt über dem PDF Viewer */
            pointer-events: none; /* Lässt normales Scrollen zu */
            display: flex;
            justify-content: space-between;
        }
        /* Style für die linke und rechte Touchzone */
        .touch-zone-left, .touch-zone-right {
            pointer-events: auto; /* Macht die Zonen klickbar */
            width: 20vw;         /* 20% des Bildschirms links/rechts sind Touch-Zonen */
            height: 100%;
            background: transparent; /* Unsichtbar */
        }
        /* Versteckt die echten Streamlit-Buttons, die wir als Trigger nutzen */
        div[data-testid="stColumn"] button {
            opacity: 0 !important;
            position: fixed;
            top: -100px;
        }
    </style>
""",
    unsafe_allow_html=True,
)


# Navigation-Logikfunktionen
def next_page():
    if st.session_state.current_page < total_pages:
        st.session_state.current_page += 1


def prev_page():
    if st.session_state.current_page > 1:
        st.session_state.current_page -= 1


# 3. DIE TRIGGER-STEUERUNG
# Kanal A: Physische PC-Tastatur (Über Ihren Key-Listener)
key = key_press_events()
if key == "ArrowRight":
    next_page()
elif key == "ArrowLeft":
    prev_page()

# Kanal B: Unsichtbare Touch-Buttons fürs Tablet
col1, col2 = st.columns(2)
with col1:
    # Versteckter Button für die linke Bildschirmhälfte
    if st.button("invisible_prev", key="btn_prev"):
        prev_page()

with col2:
    # Versteckter Button für die rechte Bildschirmhälfte
    if st.button("invisible_next", key="btn_next"):
        next_page()


# HTML-Overlay, das die unsichtbaren Zonen mit den Streamlit-Buttons verknüpft
# Wenn man links tippt, wird der echte Streamlit-Zurück-Button geklickt!
st.markdown(
    """
    <div class="touch-container">
        <div class="touch-zone-left" onclick="window.parent.document.querySelector('button[kind=\"secondary\"]').click()"></div>
        <div class="touch-zone-right" onclick="window.parent.document.querySelectorAll('button[kind=\"secondary\"]')[1].click()"></div>
    </div>
""",
    unsafe_allow_html=True,
)


# 4. AKTULLE SEITE RENDERN
pdf_viewer(
    input=pdf_bytes,
    width=1200,
    pages_to_render=[st.session_state.current_page],
)
