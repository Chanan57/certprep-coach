"""
CertPrep Coach — entry point / router.

Renders EXACTLY ONE page per run via a strict if/elif/else chain. Order matters:
quiz_started is checked BEFORE show_mode, so a running quiz can never render
together with the mode chooser (the 'Coverage shows under the quiz' bug).
"""

import streamlit as st

# initial_sidebar_state="expanded" -> the left navigator starts OPEN so the
# jump-to-question list is visible immediately. Streamlit still shows the built-in
# « / » arrow, so the user can collapse it for more reading room and reopen it
# any time. Both behaviours, no extra code.
st.set_page_config(
    page_title="CertPrep Coach",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

    ss = st.session_state

    # STRICT single-page routing — exactly one branch runs.
    if not ss.all_questions:
        show_home_page()
    elif ss.quiz_completed:
        show_results_page()
    elif ss.quiz_started:
        show_quiz_page()
    elif ss.show_mode:
        show_mode_page()
    else:
        show_home_page()


if __name__ == "__main__":
    main()
