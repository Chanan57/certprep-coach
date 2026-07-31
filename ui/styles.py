"""
Modern SaaS styling for CertPrep Coach.

Captures the indigo / lavender look: Poppins headings + Inter body, soft rounded
cards, gentle shadows, purple accents and step badges. Fonts are loaded from
Google Fonts. Every CSS class used elsewhere in the app is preserved, so this is
a drop-in replacement for the previous styles.py.
"""

import streamlit as st


def inject_css():
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@500;600;700;800&display=swap" rel="stylesheet">

        <style>
        /* ── Palette ───────────────────────────────────────────────────── */
        :root {
            --indigo:        #6C5CE7;   /* primary accent            */
            --indigo-600:    #5B4BDB;
            --indigo-700:    #4B3CC4;
            --indigo-050:    #EFEEFC;   /* soft purple fill          */
            --indigo-100:    #E4E1FA;
            --blue-info:     #3B82F6;
            --blue-050:      #EFF6FF;
            --amber-050:     #FEF6E7;
            --amber-600:     #B7791F;
            --ink:           #1E1B39;   /* near-black headings        */
            --ink-soft:      #6B6885;   /* muted text                 */
            --line:          #ECEBF3;   /* card borders               */
            --bg:            #F6F6FB;   /* app background             */
            --card:          #FFFFFF;
            --radius:        16px;
            --shadow:        0 6px 22px rgba(76, 60, 196, .06),
                             0 2px 6px rgba(30, 27, 57, .04);
            --font-body: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            --font-head: "Poppins", "Inter", -apple-system, "Segoe UI", sans-serif;
        }

        /* ── Base ──────────────────────────────────────────────────────── */
        html, body, .stApp, [data-testid="stAppViewContainer"] {
            background: var(--bg) !important;
            font-family: var(--font-body) !important;
            color: var(--ink);
        }
        .stMarkdown, .stButton, .stRadio, .stCheckbox, .stSelectbox,
        .stTextInput, .stTextArea, p, label, span, div, input, textarea, select,
        [data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] {
            font-family: var(--font-body) !important;
        }
        /* keep Material icon glyphs intact (don't force body font on them) */
        [data-testid="stIconMaterial"], .material-icons, .material-icons-outlined,
        span[class*="material-symbols"], [data-testid="stExpandIcon"] {
            font-family: 'Material Symbols Rounded','Material Symbols Outlined','Material Icons' !important;
        }

        h1, h2, h3, h4, h5 {
            font-family: var(--font-head) !important;
            color: var(--ink); font-weight: 700; letter-spacing: -.01em;
        }
        h1 {font-size: 2.4rem; font-weight: 800;}
        #MainMenu, header, footer {visibility: hidden;}
        .block-container {padding-top: 1.4rem; padding-bottom: 5rem; max-width: 1300px;}

        /* ── Cards / containers ────────────────────────────────────────── */
        [data-testid="stVerticalBlockBorderWrapper"],
        div[data-testid="stExpander"] {
            border-radius: var(--radius) !important;
            border: 1px solid var(--line) !important;
            background: var(--card);
            box-shadow: var(--shadow);
        }
        div[data-testid="stExpander"] details {border: none;}
        div[data-testid="stExpander"] summary {font-family: var(--font-head); font-weight: 600;}

        .exam-card {
            border: 1px solid var(--line); border-radius: var(--radius);
            padding: 26px 30px; background: var(--card); box-shadow: var(--shadow);
            margin-bottom: 10px; line-height: 1.65;
        }

        /* ── Buttons ───────────────────────────────────────────────────── */
        div.stButton > button {
            font-family: var(--font-body) !important; font-weight: 600;
            border-radius: 12px; border: 1px solid var(--line);
            background: #fff; color: var(--ink); padding: .5rem 1.1rem;
            transition: all .15s ease; box-shadow: 0 1px 2px rgba(30,27,57,.04);
        }
        div.stButton > button:hover {
            border-color: var(--indigo-100); background: var(--indigo-050);
            color: var(--indigo-700);
        }
        /* Primary = indigo gradient */
        div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, var(--indigo) 0%, var(--indigo-600) 100%);
            color: #fff; border: none; font-weight: 700; padding: .55rem 1.6rem;
            box-shadow: 0 6px 16px rgba(108, 92, 231, .28);
        }
        div.stButton > button[kind="primary"]:hover {
            filter: brightness(1.05); color: #fff;
            box-shadow: 0 8px 20px rgba(108, 92, 231, .38);
        }
        .reset-note button {border-radius: 20px !important;}

        /* ── Inputs ────────────────────────────────────────────────────── */
        .stTextInput input, .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div,
        .stNumberInput input {
            border-radius: 12px !important; border-color: var(--line) !important;
            background: #fff !important;
        }
        .stSelectbox div[data-baseweb="select"] > div:focus-within {
            border-color: var(--indigo) !important;
            box-shadow: 0 0 0 3px var(--indigo-050) !important;
        }

        /* ── Alerts (info/warn) rounded + tinted ───────────────────────── */
        .stAlert {border-radius: 12px; border: none;}
        div[data-baseweb="notification"] {border-radius: 12px;}

        /* ── Exam header (question view) ───────────────────────────────── */
        .exam-topbar {display: flex; justify-content: space-between; align-items: flex-start;
            border-bottom: 1px solid var(--line); padding-bottom: 10px; margin-bottom: 6px;}
        .exam-qnum {font-family: var(--font-head); font-size: 1.7rem; font-weight: 700; color: var(--ink);}
        .exam-timer-label {font-size: .68rem; letter-spacing: .14em; color: var(--ink-soft);
            text-align: right; text-transform: uppercase;}
        .exam-timer {font-family: var(--font-head); font-size: 1.6rem; font-weight: 700;
            color: var(--indigo); letter-spacing: .06em; text-align: right;}

        .prog-wrap {display: flex; gap: 26px; justify-content: center; margin: 6px 0 14px; flex-wrap: wrap;}
        .prog-item {text-align: center; min-width: 100px;}
        .prog-label {font-size: .74rem; color: var(--ink-soft); margin-bottom: 6px; white-space: nowrap;}
        .prog-bar {height: 7px; border-radius: 6px; background: var(--indigo-050); overflow: hidden;}
        .prog-fill {height: 100%; background: linear-gradient(90deg, var(--indigo), var(--indigo-600));
            border-radius: 6px;}

        .q-text {font-size: 1.02rem; color: var(--ink); line-height: 1.75;}
        .q-text strong {color: var(--ink);}

        /* ── Case study left nav ───────────────────────────────────────── */
        .cs-qcount {font-family: var(--font-head); font-weight: 700; color: var(--ink); margin-bottom: 12px;}
        .cs-nav div.stButton > button {
            width: 100%; text-align: left; justify-content: flex-start;
            border: 1px solid var(--line); border-radius: 12px; margin-bottom: 6px;
            background: #fff; color: var(--ink); font-weight: 600; padding: .6rem .8rem;
        }
        .cs-nav div.stButton > button:hover {background: var(--indigo-050); color: var(--indigo-700);}
        .cs-nav div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, var(--indigo), var(--indigo-600));
            color: #fff; border: none; box-shadow: 0 4px 12px rgba(108,92,231,.28);
        }

        /* ── Sidebar ───────────────────────────────────────────────────── */
        section[data-testid="stSidebar"] {
            background: #fff !important; border-right: 1px solid var(--line);
        }
        section[data-testid="stSidebar"] .stButton > button {border-radius: 12px;}
        section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
            font-family: var(--font-head);
        }

        /* ── Dataframe ─────────────────────────────────────────────────── */
        .stDataFrame {border: 1px solid var(--line); border-radius: 12px; overflow: hidden;}

        /* ── Tabs ──────────────────────────────────────────────────────── */
        .stTabs [data-baseweb="tab-list"] {gap: 6px;}
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px; padding: 6px 14px; font-weight: 600; color: var(--ink-soft);
        }
        .stTabs [aria-selected="true"] {background: var(--indigo-050); color: var(--indigo-700);}

        /* ── Brand + step badge helpers (usable from markdown) ─────────── */
        .brand-wrap {display: flex; align-items: center; gap: 12px; margin-bottom: 6px;}
        .brand-title {font-family: var(--font-head); font-weight: 800; font-size: 1.15rem; color: var(--ink);}
        .step-badge {display: inline-flex; align-items: center; justify-content: center;
            width: 26px; height: 26px; border-radius: 50%;
            background: var(--indigo); color: #fff; font-weight: 700; font-size: .85rem;
            margin-right: 8px;}
        .pill {display: inline-block; padding: 4px 12px; border-radius: 999px;
            background: var(--indigo-050); color: var(--indigo-700); font-weight: 600; font-size: .8rem;}
        .subtle {color: var(--ink-soft);}
        </style>
        """,
        unsafe_allow_html=True,
    )
