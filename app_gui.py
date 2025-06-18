import streamlit as st
import os
import sys # To potentially modify path if page_dewarp is not found
import argparse # To get default values from page_dewarp's parser

# Attempt to import the refactored processing function
# This might require adjusting sys.path if app_gui.py is not in a different directory
# For now, assume it's in the same directory as page_dewarp.py
try:
    from page_dewarp import run_dewarp_process, parser as page_dewarp_parser # Assuming parser is accessible
except ImportError as e:
    st.error(f"Error importing from page_dewarp.py: {e}")
    st.error("Ensure page_dewarp.py is in the same directory or accessible via PYTHONPATH.")
    # As a fallback, create a dummy parser if page_dewarp_parser can't be imported
    # This allows the UI to load for review, though processing won't work.
    if 'page_dewarp_parser' not in locals():
        st.warning("Using a dummy parser for UI display. Processing will not function correctly.")
        page_dewarp_parser = argparse.ArgumentParser()
        # Add some common arguments to the dummy parser so the UI can render
        page_dewarp_parser.add_argument('--output_zoom', type=float, default=1.0)
        page_dewarp_parser.add_argument('--output_dpi', type=int, default=300)
        page_dewarp_parser.add_argument('--page_margin_x', type=int, default=50)
        page_dewarp_parser.add_argument('--page_margin_y', type=int, default=20)
        page_dewarp_parser.add_argument('--debug_level', type=int, default=0, choices=[0,1,2,3])


st.set_page_config(layout="wide")
st.title("Page Dewarping Tool")

st.sidebar.header("Upload Images")
uploaded_files = st.sidebar.file_uploader("Choose image(s)...", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

st.sidebar.header("Dewarping Parameters")

# Function to get default value from parser
def get_default(param_name):
    for action in page_dewarp_parser._actions:
        if hasattr(action, 'dest') and action.dest == param_name: # Check if action has dest
            return action.default
    return None

# --- Basic Parameters ---
st.sidebar.subheader("Output Settings")
output_zoom = st.sidebar.slider("Output Zoom", 0.5, 3.0, get_default('output_zoom') or 1.0, 0.1)
output_dpi = st.sidebar.number_input("Output DPI", 50, 600, get_default('output_dpi') or 300, 50)

st.sidebar.subheader("Page Margins")
page_margin_x = st.sidebar.slider("Page Margin X (px)", 0, 200, get_default('page_margin_x') or 50, 5)
page_margin_y = st.sidebar.slider("Page Margin Y (px)", 0, 200, get_default('page_margin_y') or 20, 5)

# --- Advanced Parameters (Collapsible) ---
with st.sidebar.expander("Advanced Settings"):
    debug_level = st.select_slider("Debug Level", options=[0, 1, 2, 3], value=get_default('debug_level') or 0)

    # Example: Add more parameters here if needed, getting defaults from page_dewarp_parser
    # focal_length = st.slider("Focal Length", 0.5, 2.5, get_default('focal_length') or 1.2, 0.1)
    # adaptive_winsz = st.slider("Adaptive Window Size", 5, 105, get_default('adaptive_winsz') or 55, step=2) # Must be odd

# Placeholder for where parameters will be collected
current_params_from_ui = {
    'output_zoom': output_zoom,
    'output_dpi': output_dpi,
    'page_margin_x': page_margin_x,
    'page_margin_y': page_margin_y,
    'debug_level': debug_level,
    # 'focal_length': focal_length, # Uncomment if added above
    # 'adaptive_winsz': adaptive_winsz # Uncomment if added above
    # ... add other necessary parameters here, ensuring they match what run_dewarp_process expects
    # and that their defaults are correctly obtained or set.
}

# Get all default arguments from the parser to ensure params_dict is complete
# This is crucial for run_dewarp_process
default_args = {}
for action in page_dewarp_parser._actions:
    if hasattr(action, 'dest') and action.dest != argparse.SUPPRESS: # Exclude help actions etc.
        # Skip positional arguments like 'images' if they are in the parser for CLI
        if action.option_strings: # This usually means it's an optional argument like --foo
            default_args[action.dest] = action.default

# Update params_dict with defaults, then with user selected values
# This ensures any param not in the UI gets its default value
final_params = {**default_args, **current_params_from_ui}


st.header("Uploaded Images")
if uploaded_files:
    cols = st.columns(3) # Display images in 3 columns
    for i, uploaded_file in enumerate(uploaded_files):
        cols[i % 3].image(uploaded_file, caption=uploaded_file.name, use_column_width=True)
else:
    st.info("Please upload one or more images to begin.")

if st.button("Dewarp Image(s)"):
    if uploaded_files:
        st.info("Processing... (This section will show results in the next step)")
        # Logic for processing and displaying results will be added in the next plan step.
        # For now, just display the parameters that would be used.
        st.subheader("Parameters to be used for processing:")
        st.json(final_params) # Display all parameters that would be passed
    else:
        st.warning("Please upload at least one image.")

# To run this app: streamlit run app_gui.py
