"""
CertPrep Coach — entry point / router.

Renders EXACTLY ONE page per run via a strict if/elif/else chain. The priority
order below guarantees the quiz never renders together with the mode chooser
(the bug where setup controls leaked beneath the live question):

    quiz_completed  -> results/report
    quiz_started    -> the quiz  (takes priority over show_mode)
    show_mode       -> mode chooser
    (no questions)  -> home
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

    ss = st.session_state

    # Strict single-page routing. Order matters: quiz_started is checked BEFORE
    # show_mode so a running quiz can never render alongside the setup page.
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
