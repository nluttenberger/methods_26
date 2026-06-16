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
    "Use the left and right arrow keys / use swipe left, swipe right to navigate."
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

# 3. DER REINE KEY-LISTENER (Steuert nun Tasten und Swipes!)
key = key_press_events()

if key == "ArrowRight" and st.session_state.current_page < total_pages:
    st.session_state.current_page += 1
    st.rerun()
elif key == "ArrowLeft" and st.session_state.current_page > 1:
    st.session_state.current_page -= 1
    st.rerun()


# --- ELEGANTER JAVASCRIPT GESTURE LISTENER ---
# Übersetzt Wischgesten in native Events, die key_press_events direkt versteht
gesture_js = """
<script>
    let touchstartX = 0;
    let touchendX = 0;
    const minSwipeDistance = 50; 
    const mainWin = window.parent;

    function handleSwipe() {
        let swipeDistance = touchendX - touchstartX;
        if (Math.abs(swipeDistance) > minSwipeDistance) {
            
            // Bestimme die simulierte Taste basierend auf der Wischrichtung
            // Nach LINKS wischen -> Weiterblättern (ArrowRight)
            // Nach RECHTS wischen -> Zurückblättern (ArrowLeft)
            let simulatedKey = swipeDistance > 0 ? "ArrowLeft" : "ArrowRight";
            
            // Erzeuge ein Event, das exakt so aussieht, als hätte der Nutzer eine Taste gedrückt
            let event = new mainWin.KeyboardEvent('keydown', {
                key: simulatedKey,
                code: simulatedKey,
                bubbles: true,
                composed: true
            });
            
            // Sende es an das Hauptfenster, wo streamlit_keypress darauf lauscht
            mainWin.dispatchEvent(event);
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
            console.log("iFrame blockiert:", e);
        }
    }

    // Listener auf dem Haupt-Dokument aktivieren
    addListeners(mainWin.document);

    // Listener in die iFrames (PDF Viewer) injizieren
    let iframeCheckAttempts = 0;
    const iframeInterval = setInterval(() => {
        iframeCheckAttempts++;
        const iframes = mainWin.document.querySelectorAll('iframe');
        if (iframes.length > 1 || iframeCheckAttempts > 10) {
            iframes.forEach(iframe => {
                if (iframe.contentDocument) {
                    addListeners(iframe.contentDocument);
                }
            });
            clearInterval(iframeInterval);
        }
    }, 500); 
</script>
"""

# Rendert das JS-Skript unsichtbar im Hintergrund
html(gesture_js, height=0, width=0)

# 4. AKTULLE SEITE RENDERN
pdf_viewer(
    input=pdf_bytes,
    width=1200,
    pages_to_render=[st.session_state.current_page],
)
