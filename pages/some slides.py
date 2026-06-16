import io
import requests
import streamlit as st
from pypdf import PdfReader
from streamlit.components.v1 import html
from streamlit_keypress import key_press_events
from streamlit_pdf_viewer import pdf_viewer

st.title("Some slides")
st.write(
    'from my presentation at the KIT "Bundestagsreden-Seminar" in June 2026\n\n'
)
st.write(
    "Use the left and right arrow keys/use swipe left, swipe right to navigate through the slides."
)

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

# --- NEU: VERSTECKTES SCHNITTSTELLEN-INPUT FÜR TABLETS ---
# Wir verstecken das Eingabefeld unsichtbar im Hintergrund mittels CSS
st.markdown(
    """
    <style>
        div[data-testid="stTextInput"] {
            display: none !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# Dieses Feld empfängt die Wischgesten vom JavaScript
swipe_action = st.text_input(
    "Swipe Receiver", key="swipe_receiver", label_visibility="collapsed"
)


# 3. WEGE ZUM UMBLÄTTERN (Taste ODER Wischgeste)
def next_page():
    if st.session_state.current_page < total_pages:
        st.session_state.current_page += 1


def prev_page():
    if st.session_state.current_page > 1:
        st.session_state.current_page -= 1


# Weg A: Physischer Key-Listener (Pfeiltasten am PC)
key = key_press_events()
if key == "ArrowRight":
    next_page()
elif key == "ArrowLeft":
    prev_page()

# Weg B: Touch-Gesten-Auswertung (Vom Tablet via JavaScript)
if swipe_action == "Right":
    next_page()
    st.rerun()  # Sofortiger UI-Refresh nach dem Wischen
elif swipe_action == "Left":
    prev_page()
    st.rerun()


# --- JAVASCRIPT GESTURE LISTENER (Korrigiert & Optimiert) ---
gesture_js = """
<script>
    let touchstartX = 0;
    let touchendX = 0;
    const minSwipeDistance = 60; // Mindestdistanz für Wisch in Pixeln

    // Greift auf das Hauptfenster von Streamlit zu
    const mainDoc = window.parent.document;

    function handleSwipe() {
        let swipeDistance = touchendX - touchstartX;
        
        if (Math.abs(swipeDistance) > minSwipeDistance) {
            // Findet das unsichtbare Streamlit-Eingabefeld im Hauptfenster
            const targetInput = mainDoc.querySelector("input[aria-label='Swipe Receiver']");
            
            if (targetInput) {
                if (swipeDistance > 0) {
                    // Von links nach rechts gewischt -> Zurückblättern
                    targetInput.value = "Right";
                } else {
                    // Von rechts nach links gewischt -> Vorwärtsblättern
                    targetInput.value = "Left";
                }
                
                // Triggert das Event, damit Streamlit die Änderung sofort bemerkt
                targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                
                // Setzt das Feld nach einem kurzen Moment zurück, um dieselbe Geste wieder zu erlauben
                setTimeout(() => {
                    targetInput.value = "";
                    targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                }, 150);
            }
        }
    }

    // Event-Listener auf das gesamte Dokument (window.parent) legen
    mainDoc.addEventListener('touchstart', e => {
        touchstartX = e.changedTouches[0].screenX;
    }, { passive: true });

    mainDoc.addEventListener('touchend', e => {
        touchendX = e.changedTouches[0].screenX;
        handleSwipe();
    }, { passive: true });
</script>
"""

# Rendert das JS-Skript unsichtbar
html(gesture_js, height=0, width=0)

# 4. Aktuelle Seite rendern
pdf_viewer(
    input=response.content,
    width=1200,
    pages_to_render=[
        st.session_state.current_page
    ],  # Übergibt die aktuelle Seite als Liste
)
