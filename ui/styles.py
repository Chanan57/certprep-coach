"""
Fluent-style CSS for CertPrep Coach.

Restyles Streamlit to resemble the Microsoft certification exam UI:
  - Segoe UI font (native on Windows, graceful fallback elsewhere)
  - Microsoft / Fluent colour palette (exposed as CSS variables for easy tweaks)
  - Flat, square-cornered buttons, cards, borders and radios

All class names match those used across the ui/ package, so this file is a
drop-in replacement for the previous styles.py.
"""

import streamlit as st


def inject_css():
    st.markdown(
        """
        <style>
        /* ---- Fluent palette (tweak here) ------------------------------- */
        :root {
            --ms-navy:      #17324D;   /* primary buttons / progress fill   */
            --ms-navy-dark: #0F2740;   /* hover                             */
            --ms-blue:      #0078D4;   /* Microsoft accent blue             */
            --ms-blue-dark: #106EBE;   /* accent hover                      */
            --ms-ink:       #201F1E;   /* Fluent default text               */
            --ms-ink-soft:  #605E5C;   /* secondary text                    */
            --ms-line:      #E1DFDD;   /* Fluent neutral border             */
            --ms-line-soft: #EDEBE9;   /* lighter divider                   */
            --ms-bg:        #FFFFFF;
            --ms-bg-alt:    #FAF9F8;   /* Fluent neutralLighter             */
            --ms-hover:     #F3F2F1;   /* Fluent neutralLighterAlt hover    */
            --font: "Segoe UI", "Segoe UI Web (West European)", -apple-system,
                    BlinkMacSystemFont, Roboto, "Helvetica Neue", Arial, sans-serif;
        }

        /* ---- Global font + chrome -------------------------------------- */
        /* Apply Segoe UI to TEXT elements only. We deliberately avoid a blanket
           'span' / '*' rule: Streamlit's dropdown & expander chevrons are
           Material Symbols icon *ligatures* (e.g. "expand_more"). Forcing a text
           font onto them makes the raw ligature words show up in the UI. */
        html, body, .stApp, .stMarkdown, .stButton, .stRadio, .stCheckbox,
        .stSelectbox, .stTextInput, .stTextArea, input, textarea, button,
        select, h1, h2, h3, h4, h5, h6, p, label,
        [data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] {
            font-family: var(--font) !important;
        }
        /* Restore the Material icon font on icon glyphs so chevrons render
           correctly instead of showing "expand_more" / "arrow_drop_down". */
        [data-testid="stIconMaterial"], .material-icons, .material-icons-outlined,
        span[class*="material-symbols"], [data-testid="stExpandIcon"],
        [data-testid="stSelectboxVirtualDropdown"] span {
            font-family: 'Material Symbols Rounded', 'Material Symbols Outlined',
                         'Material Icons' !important;
        }
        body, .stApp {color: var(--ms-ink);}
        #MainMenu, header, footer {visibility: hidden;}
        .block-container {padding-top: 1rem; padding-bottom: 6rem; max-width: 1500px;}

        h1, h2, h3, h4 {color: var(--ms-ink); font-weight: 600;}

        /* ---- Exam top bar ---------------------------------------------- */
        .exam-topbar {
            display: flex; justify-content: space-between; align-items: flex-start;
            border-bottom: 1px solid var(--ms-line); padding-bottom: 10px; margin-bottom: 6px;
        }
        .exam-qnum {font-size: 1.55rem; font-weight: 600; color: var(--ms-ink);}
        .exam-timer-label {
            font-size: .68rem; letter-spacing: .14em; color: var(--ms-ink-soft);
            text-align: right; text-transform: uppercase;
        }
        .exam-timer {
            font-size: 1.55rem; font-weight: 600; color: var(--ms-navy);
            letter-spacing: .1em; text-align: right; font-variant-numeric: tabular-nums;
        }

        /* ---- Progress segments ----------------------------------------- */
        .prog-wrap {display: flex; gap: 26px; justify-content: center; margin: 4px 0 12px 0; flex-wrap: wrap;}
        .prog-item {text-align: center; min-width: 96px;}
        .prog-label {font-size: .72rem; color: var(--ms-ink-soft); margin-bottom: 5px; white-space: nowrap;}
        .prog-bar {height: 6px; border-radius: 0; background: var(--ms-line); overflow: hidden;}
        .prog-fill {height: 100%; background: var(--ms-navy); border-radius: 0;}

        /* ---- Question card --------------------------------------------- */
        .exam-card {
            border: 1px solid var(--ms-line); border-radius: 2px; padding: 26px 30px;
            background: var(--ms-bg); box-shadow: 0 1.6px 3.6px rgba(0,0,0,.08),
            0 .3px .9px rgba(0,0,0,.06); margin-bottom: 8px; line-height: 1.6;
        }
        .exam-instr {color: var(--ms-ink); line-height: 1.6; margin-bottom: 10px;}
        .q-text {font-size: 1rem; color: var(--ms-ink); line-height: 1.7;}
        .q-text strong {color: var(--ms-ink); font-weight: 600;}

        /* ---- Buttons (Fluent flat) ------------------------------------- */
        div.stButton > button {
            font-family: var(--font) !important; border-radius: 2px;
            border: 1px solid var(--ms-line); background: var(--ms-bg);
            color: var(--ms-ink); font-weight: 600; transition: background .12s ease;
        }
        div.stButton > button:hover {background: var(--ms-hover); border-color: var(--ms-line);}

        /* Primary = navy (Previous / Next / Finish / Start) */
        div.stButton > button[kind="primary"] {
            background: var(--ms-navy); color: #fff; border: 1px solid var(--ms-navy);
            border-radius: 2px; font-weight: 600; padding: .5rem 1.8rem;
        }
        div.stButton > button[kind="primary"]:hover {
            background: var(--ms-navy-dark); border-color: var(--ms-navy-dark);
        }

        .reset-note button {border-radius: 16px !important;}

        /* ---- Radios & checkboxes (tighter, Fluent-ish) ----------------- */
        .stRadio > div {gap: .35rem;}
        .stRadio label, .stCheckbox label {color: var(--ms-ink); font-weight: 400;}

        /* ---- Inputs ---------------------------------------------------- */
        .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
            border-radius: 2px !important;
        }

        /* ---- Links / accent -------------------------------------------- */
        a, a:visited {color: var(--ms-blue);}
        a:hover {color: var(--ms-blue-dark);}

        /* ---- Alerts: flatten Streamlit's rounded pills ----------------- */
        .stAlert {border-radius: 2px;}

        /* ---- Case study left navigation -------------------------------- */
        .cs-qcount {font-weight: 600; color: var(--ms-ink); margin-bottom: 12px; line-height: 1.4;}
        .cs-panel-wrap {border-right: 1px solid var(--ms-line); padding-right: 8px;}

        .cs-nav div.stButton > button {
            width: 100%; text-align: left; justify-content: flex-start;
            border: none; border-bottom: 1px solid var(--ms-line-soft); border-radius: 0;
            background: transparent; color: var(--ms-navy); font-weight: 400;
            padding: .6rem .5rem;
        }
        .cs-nav div.stButton > button:hover {background: var(--ms-hover);}
        .cs-nav div.stButton > button[kind="primary"] {
            background: var(--ms-bg-alt); color: var(--ms-ink); font-weight: 600;
            border-left: 3px solid var(--ms-navy); border-bottom: 1px solid var(--ms-line-soft);
        }

        /* ---- Sidebar ---------------------------------------------------- */
        section[data-testid="stSidebar"] {background: var(--ms-bg-alt); border-right: 1px solid var(--ms-line);}
        section[data-testid="stSidebar"] .stButton > button {border-radius: 2px;}

        /* ---- Dataframes ------------------------------------------------- */
        .stDataFrame {border: 1px solid var(--ms-line); border-radius: 2px;}
        </style>
        """,
        unsafe_allow_html=True,
    )
