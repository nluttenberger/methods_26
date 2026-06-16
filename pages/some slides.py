import io
import os
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

# 1. DATEINAME DEFINIEREN (Relativ im selben Repository-Ordner)
# Platzieren Sie "Dashboard 07.pdf" einfach in Ihrem Git-Repository neben der app.py
pdf_filename = "Dashboard 07.pdf"


@st.cache_data(show_spinner=False)
def load_pdf_file(filename):
    with open(filename, "rb") as f:
        pdf_bytes = f.read()
    pdf_file = io.BytesIO(pdf_bytes)
    reader = PdfReader(pdf_file)
    total_pages = len(reader.pages)
    return pdf_bytes, total_pages


# Krisensicherer Ladevorgang ohne Internet/Netzwerk-Requests
if os.path.exists(pdf_filename):
    pdf_bytes, total_pages = load_pdf_file(pdf_filename)
else:
    st.error(
        f"⚠️ Datei '{pdf_filename}' wurde im Verzeichnis nicht gefunden! "
        "Bitte stellen Sie sicher, dass die PDF-Datei im selben Ordner wie Ihre app.py liegt."
    )
    st.stop()

# 2. AKTULLE SEITE INITIALISIEREN
if "current_page" not in st.session_state:
    st.session_state.current_page = 1

# --- UNSICHTBARES TEXTFELD FÜR GESTEN ---
st.markdown(
    "<style>div[data-testid='stTextInput'] { display: none !important; }</style>",
    unsafe_allow_html=True,
)
# Empfängt die Wörter "Left" oder "Right" aus dem JavaScript
swipe_action = st.text_input(
    "", key="swipe_receiver", label_visibility="collapsed"
)

# 3. DIE NAVIGATIONSLOGIK (Tastatur ODER Wisch-Events)
key = key_press_events()

# Auswertung: Nächste Seite (PfeilRechts ODER Wisch nach Links)
if (key == "ArrowRight" or swipe_action == "Left") and (
    st.session_state.current_page < total_pages
):
    st.session_state.current_page += 1
    st.rerun()

# Auswertung: Vorherige Seite (PfeilLinks ODER Wisch nach Rechts)
elif (key == "ArrowLeft" or swipe_action == "Right") and (
    st.session_state.current_page > 1
):
    st.session_state.current_page -= 1
    st.rerun()


# --- JAVASCRIPT FOR TOUCH GESTURES (Cloud-optimiert) ---
gesture_js = """
<script>
    let touchstartX = 0;
    let touchendX = 0;
    const minSwipeDistance = 50; 
    const mainDoc = window.parent.document;

    function handleSwipe() {
        let swipeDistance = touchendX - touchstartX;
        if (Math.abs(swipeDistance) > minSwipeDistance) {
            const targetInput = mainDoc.querySelector("input[aria-label='']");
            if (targetInput) {
                targetInput.value = swipeDistance > 0 ? "Right" : "Left";
                targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                
                setTimeout(() => {
                    targetInput.value = "";
                    targetInput.dispatchEvent(new Event('input', { bubbles: true }));
                }, 100);
            }
        }
    }

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
            console.log("Konnte Listener nicht binden:", e);
        }
    }

    // An Hauptbildschirm binden
    addListeners(mainDoc);

    // An den iFrame des PDF-Viewers binden (Intervall fängt verzögertes Laden ab)
    let iframeCheckAttempts = 0;
    const iframeInterval = setInterval(() => {
        iframeCheckAttempts++;
        const iframes = mainDoc.querySelectorAll('iframe');
        if (iframes.length > 1 || iframeCheckAttempts > 10) {
            iframes.forEach(iframe => {
                if (iframe.contentDocument) {
                    addListeners(iframe.contentDocument);
                }
            });
            clearInterval(iframeInterval); // Stoppen, sobald gekoppelt
        }
    }, 500); 
</script>
"""

html(gesture_js, height=0, width=0)

# 4. AKTULLE SEITE RENDERN
pdf_viewer(
    input=pdf_bytes,
    width=1200,
    pages_to_render=[st.session_state.current_page],
)
