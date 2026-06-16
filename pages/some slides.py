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

# Raw-Download-URL von GitHub
pdf_url = "https://githubusercontent.com"


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

# --- INPUT FÜR TABLET-GESTEN ---
# Wir verstecken das Eingabefeld per CSS
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

# Dieses unsichtbare Feld fängt die Wischgesten auf
swipe_action = st.text_input(
    "Swipe Receiver", key="swipe_receiver", label_visibility="collapsed"
)


# Navigation-Hilfsfunktionen
def next_page():
    if st.session_state.current_page < total_pages:
        st.session_state.current_page += 1


def prev_page():
    if st.session_state.current_page > 1:
        st.session_state.current_page -= 1


# 3. AUSWERTUNG DER SIGNALE (Tastatur ODER Touch)
# Physischer Key-Listener (Pfeiltasten am PC)
key = key_press_events()
if key == "ArrowRight":
    next_page()
elif key == "ArrowLeft":
    prev_page()

# Touch-Gesten (Vom Tablet via JavaScript)
if swipe_action == "Right":
    prev_page()  # Nach rechts wischen = vorherige Seite
    st.rerun()
elif swipe_action == "Left":
    next_page()  # Nach links wischen = nächste Seite
    st.rerun()


# --- NEUER, KORRIGIERTER JAVASCRIPT GESTURE LISTENER ---
# Dieses Skript bindet sich an den Hauptbildschirm UND an alle iFrames (wie den PDF Viewer)
gesture_js = """
<script>
    let touchstartX = 0;
    let touchendX = 0;
    const minSwipeDistance = 50; // Pixel-Mindestdistanz für einen Wisch

    const mainDoc = window.parent.document;

    function handleSwipe() {
        let swipeDistance = touchendX - touchstartX;
        if (Math.abs(swipeDistance) > minSwipeDistance) {
            const targetInput = mainDoc.querySelector("input[aria-label='Swipe Receiver']");
            if (targetInput) {
                // Wert setzen
                targetInput.value = swipeDistance > 0 ? "Right" : "Left";
                // Event absenden, damit Streamlit es merkt
                targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                
                // Feld leeren für die nächste Geste
                setTimeout(() => {
                    targetInput.value = "";
                    targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                }, 100);
            }
        }
    }

    // Funktion registriert die Touch-Events auf einem bestimmten Dokument-Objekt
    function addListeners(targetDoc) {
        try {
            targetDoc.addEventListener('touchstart', e => {
                touchstartX = e.changedTouches[0].screenX;
            }, { passive: true });

            targetDoc.addEventListener('touchend', e => {
                touchendX = e.changedTouches[0].screenX;
                handleSwipe();
            }, { passive: true });
        } catch (e) {
            // Verhindert Abstürze, falls ein iFrame blockiert ist (Sicherheitsrichtlinien)
            console.log("Konnte Listener nicht an iFrame binden:", e);
        }
    }

    # Binde an das Hauptfenster
    addListeners(mainDoc);

    # SUPER-TRICK: Binde an alle iFrames (wichtig für den PDF-Viewer!)
    setTimeout(() => {
        const iframes = mainDoc.querySelectorAll('iframe');
        iframes.forEach(iframe => {
            if (iframe.contentDocument) {
                addListeners(iframe.contentDocument);
            }
        });
    }, 1500); // Wartet 1.5s, bis der PDF-Viewer fertig geladen ist
</script>
"""

# Rendert das JS-Skript im Hintergrund
html(gesture_js, height=0, width=0)

# 4. Aktuelle Seite rendern
pdf_viewer(
    input=response.content,
    width=1200,
    pages_to_render=[st.session_state.current_page],
)
