import streamlit as st
import requests
from streamlit_pdf_viewer import pdf_viewer
import io
from pypdf import PdfReader
from streamlit_keypress import key_press_events
from streamlit.components.v1 import html

st.title("Some slides")
st.write("from my presentation at the KIT \"Bundestagsreden-Seminar\" in June 2026\n\n")
st.write("Use the left and right arrow keys/use swipe left, swipe right to navigate through the slides.")

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

# --- JAVASCRIPT GESTURE LISTENER ---
# Lauscht auf Wischgesten und triggert ein künstliches Tastatur-Event
gesture_js = """
<script>
    let touchstartX = 0;
    let touchendX = 0;
    const minSwipeDistance = 70; // Pixel-Mindestdistanz für einen Wisch

    // Zugriff auf das Haupt-Dokument der Streamlit-App
    const doc = window.parent.document;

    function handleSwipe() {
        let swipeDistance = touchendX - touchstartX;
        
        if (Math.abs(swipeDistance) > minSwipeDistance) {
            if (swipeDistance > 0) {
                // Wisch nach RECHTS -> Simuliert Pfeiltaste Links (Zurückblättern)
                doc.dispatchEvent(new KeyboardEvent('keydown', {'key': 'ArrowLeft'}));
            } else {
                // Wisch nach LINKS -> Simuliert Pfeiltaste Rechts (Vorwärtsblättern)
                doc.dispatchEvent(new KeyboardEvent('keydown', {'key': 'ArrowRight'}));
            }
        }
    }

    doc.addEventListener('touchstart', e => {
        touchstartX = e.changedTouches[0].screenX;
    }, { passive: true });

    doc.addEventListener('touchend', e => {
        touchendX = e.changedTouches[0].screenX;
        handleSwipe();
    }, { passive: true });
</script>
"""

# Rendert das Skript sicher im Hintergrund (wichtig: Funktion aus dem Import!)
html(gesture_js, height=0, width=0)

# 4. Aktuelle Seite rendern
pdf_viewer(
    input=response.content,
    width=1200,
    pages_to_render=[st.session_state.current_page]  # Übergibt die aktuelle Seite als Liste
)
