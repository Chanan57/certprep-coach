"""
Minimal drag-and-drop test — run this ALONE to check streamlit-sortables works.

    streamlit run test_dragdrop.py

If you can drag the cards between the two columns here, the library works and
the problem is in the app (restart / seeding). If this page errors or shows no
drag board, the library itself isn't installed/importing correctly.
"""

import streamlit as st

st.title("🧪 Drag-and-drop library test")

# 1) Does it import at all?
try:
    from streamlit_sortables import sort_items
    st.success("✅ streamlit_sortables imported OK")
except Exception as e:  # noqa
    st.error(f"❌ Import FAILED: {e}")
    st.info("Fix: run  →  pip install streamlit-sortables  ←  in the SAME "
            "environment that runs Streamlit, then fully restart.")
    st.stop()

st.write("Drag the actions from the left column into the answer area on the right:")

# 2) Two-container drag board
containers = [
    {"header": "📋 Actions (available)",
     "items": ["Create a sensitivity label.",
               "Create a sensitive info type.",
               "Create an auto-labeling policy.",
               "Wait 24 hours and then turn on the policy."]},
    {"header": "✅ Answer Area (your order)", "items": []},
]

arranged = sort_items(containers, multi_containers=True, key="test_board")

st.markdown("---")
st.subheader("Your current arrangement")
for c in arranged:
    st.markdown(f"**{c['header']}**")
    for i, item in enumerate(c["items"], 1):
        st.write(f"{i}. {item}")

st.caption("If you could drag items above, the library works. 🎉")
