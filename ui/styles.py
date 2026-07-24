"""CSS to make Streamlit resemble the Microsoft exam UI."""

import streamlit as st


def inject_css():
    st.markdown(
        """
        <style>
        #MainMenu, header, footer {visibility: hidden;}
        .block-container {padding-top: 1rem; padding-bottom: 6rem; max-width: 1400px;}

        .exam-topbar {
            display: flex; justify-content: space-between; align-items: flex-start;
            border-bottom: 1px solid #e6e6e6; padding-bottom: 8px; margin-bottom: 4px;
        }
        .exam-qnum {font-size: 1.5rem; font-weight: 700; color: #1b1b1b;}
        .exam-timer-label {font-size: .7rem; letter-spacing: .12em; color: #444; text-align: right;}
        .exam-timer {font-size: 1.6rem; font-weight: 600; color: #17324d; letter-spacing: .08em; text-align: right;}

        .prog-wrap {display: flex; gap: 22px; justify-content: center; margin: 2px 0 10px 0; flex-wrap: wrap;}
        .prog-item {text-align: center; min-width: 90px;}
        .prog-label {font-size: .72rem; color: #333; margin-bottom: 4px; white-space: nowrap;}
        .prog-bar {height: 7px; border-radius: 4px; background: #d9d9d9; overflow: hidden;}
        .prog-fill {height: 100%; background: #17324d; border-radius: 4px;}

        .exam-card {
            border: 1px solid #e2e2e2; border-radius: 6px; padding: 26px 28px;
            background: #fff; box-shadow: 0 1px 2px rgba(0,0,0,.04); margin-bottom: 8px;
        }
        .exam-instr {color: #17324d; line-height: 1.6; margin-bottom: 10px;}

        div.stButton > button[kind="primary"] {
            background: #17324d; color: #fff; border: none; border-radius: 4px;
            font-weight: 700; padding: .5rem 1.6rem;
        }
        div.stButton > button[kind="primary"]:hover {background: #24466b;}

        .reset-note button {border-radius: 20px !important;}

        .cs-panel {border-right: 1px solid #e2e2e2; padding-right: 10px;}
        .cs-qcount {font-weight: 700; color: #1b1b1b; margin-bottom: 8px;}
        </style>
        """,
        unsafe_allow_html=True,
    )
