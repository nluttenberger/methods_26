# Graphviz Layout Comparison Dashboard

Run the dashboard with:

```bash
pip install -r requirements.txt
# Ensure Graphviz is installed on your system (dot, fdp)
streamlit run dashboard_streamlit.py
```

The app renders two configurations side-by-side, allows toggling `fixedsize`, `width`, `height`, `margin`, and visualizes the layout engine's bounding boxes. Use the export button to download SVGs and layout logs.
