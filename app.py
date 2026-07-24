"""
CertPrep Coach — entry point.

Thin router: wires the ui/ package together and routes between pages based on
session state. All UI logic lives in ui/, all data logic in src/.
"""

import streamlit as st

st.set_page_config(page_title="CertPrep Coach", page_icon="📘", layout="wide")

from ui.state import initialise_session_state
from ui.styles import inject_css
from ui.pages import (
    show_home_page,
    show_mode_page,
    show_quiz_page,
    show_results_page,
)


def main():
    initialise_session_state()
    inject_css()

    if not st.session_state.all_questions:
        show_home_page()
    elif st.session_state.quiz_completed:
        show_results_page()
    elif st.session_state.quiz_started:
        show_quiz_page()
    elif st.session_state.show_mode:
        show_mode_page()
    else:
        show_home_page()


if __name__ == "__main__":
    main()
