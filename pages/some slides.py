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

# --- MULTI-CHANNEL NAVIGATIONSLOGIK ---


# Hilfsfunktionen für das Blättern
def page_forward():
    if st.session_state.current_page < total_pages:
        st.session_state.current_page += 1


def page_backward():
    if st.session_state.current_page > 1:
        st.session_state.current_page -= 1


# Kanal A: Physische PC-Tastatur (Über Ihren Key-Listener)
key = key_press_events()
if key == "ArrowRight":
    page_forward()
elif key == "ArrowLeft":
    page_backward()

# Kanal B: Tablet Wischgesten (Über die URL-Query-Parameter-Brücke)
# Das JavaScript schreibt das Event direkt in die URL, Streamlit liest es aus
query_params = st.query_params
if "swipe" in query_params:
    action = query_params["swipe"]
    # Parameter sofort löschen, damit es beim nächsten Rerun nicht wieder triggert
    st.query_params.clear()

    if action == "Left":  # Wisch nach links -> Nächste Seite
        page_forward()
        st.rerun()
    elif action == "Right":  # Wisch nach rechts -> Vorherige Seite
        page_backward()
        st.rerun()


# --- JAVASCRIPT GESTURE LISTENER (Über Query-Parameter-Brücke) ---
# Schreibt bei einem Swipe die Aktion direkt in die URL der Streamlit App.
# Das funktioniert plattformübergreifend auf jedem Tablet (iPad & Android)!
gesture_js = """
<script>
    let touchstartX = 0;
    let touchendX = 0;
    const minSwipeDistance = 60; // Mindestdistanz für Wisch in Pixeln
    const mainWin = window.parent;

    function handleSwipe() {
        let swipeDistance = touchendX - touchstartX;
        if (Math.abs(swipeDistance) > minSwipeDistance) {
            let direction = swipeDistance > 0 ? "Right" : "Left";
            
            // Ermittle die aktuelle URL des Streamlit-Hauptfensters
            let currentUrl = new URL(mainWin.location.href);
            // Setze den Query-Parameter ?swipe=Left oder ?swipe=Right
            currentUrl.searchParams.set("swipe", direction);
            
            // Aktualisiere das Hauptfenster. Streamlit erkennt dies sofort als Rerun-Signal!
            mainWin.location.replace(currentUrl.href);
        }
    }

    function addListeners(targetDoc) {
        try {
            targetDoc.addEventListener('touchstart', e => {
                // screenX aus dem ersten Touch-Event auslesen
                touchstartX = e.changedTouches[0].screenX;
            }, { passive: true });

            targetDoc.addEventListener('touchend', e => {
                touchendX = e.changedTouches[0].screenX;
                handleSwipe();
            }, { passive: true });
        } catch (e) {
            console.log("iFrame blockiert oder noch nicht bereit:", e);
        }
    }

    // 1. An Hauptbildschirm binden
    addListeners(mainWin.document);

    // 2. An den iFrame des PDF-Viewers binden (Scan-Schleife für verzögertes Laden)
    let iframeCheckAttempts = 0;
    const iframeInterval = setInterval(() => {
        iframeCheckAttempts++;
        const iframes = mainWin.document.querySelectorAll('iframe');
        if (iframes.length > 1 || iframeCheckAttempts > 15) {
            iframes.forEach(iframe => {
                if (iframe.contentDocument) {
                    addListeners(iframe.contentDocument);
                }
            });
            clearInterval(iframeInterval);
        }
    }, 400); 
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
