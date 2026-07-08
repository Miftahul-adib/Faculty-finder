import streamlit as st
from utils import BASE_CSS, APP_NAME, APP_ICON

st.set_page_config(page_title=APP_NAME, page_icon=APP_ICON,
                   layout="centered", initial_sidebar_state="expanded")
st.markdown(BASE_CSS, unsafe_allow_html=True)
st.logo("assets/logo.svg", icon_image="assets/logo_icon.svg")

home           = st.Page("views/home.py", title="Home", default=True)
search_faculty = st.Page("pages/1_Search_Faculty.py", title="Search Faculty")
search_phd     = st.Page("pages/2_Search_PhD_Students.py", title="Search PhD Students")
profile        = st.Page("pages/3_My_Profile.py", title="My Profile")

# Rendered manually (instead of Streamlit's auto nav) so the sidebar's
# contents are always fully visible, with no collapse/hide behavior.
with st.sidebar:
    st.page_link(home)
    st.page_link(search_faculty)
    st.page_link(search_phd)
    st.page_link(profile)

pg = st.navigation([home, search_faculty, search_phd, profile], position="hidden")
pg.run()
