# SafeChild NGO/Admin Dashboard - FULL INTEGRATION

from azure_cognitive_integration import analyze_text_entities
from translator_utils import translate_text  # if translation is required
from cosmos_Utils import get_reports, update_status, get_blacklisted_locations
import streamlit as st
from streamlit_folium import st_folium
import requests
from streamlit_lottie import st_lottie
import pandas as pd
import os
import folium
import logging
def rerun():
    
    st.warning("Please refresh the page to see updated data.")


logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

def azure_maps_search_place(query, limit=5):
    key = os.getenv("AZURE_MAPS_KEY")
    if not key:
        st.error("Azure Maps key not configured. Please set the AZURE_MAPS_KEY environment variable.")
        return []
    url = "https://atlas.microsoft.com/search/address/json"
    params = {
        "api-version": "1.0",
        "subscription-key": key,
        "query": query,
        "limit": limit
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            st.error(f"Azure Maps API error: {response.status_code} {response.text}")
            logging.error(f"Azure Maps API error: {response.status_code} {response.text}")
            return []
        data = response.json()
        return data.get("results", [])
    except requests.RequestException as e:
        st.error(f"Network error occurred while calling Azure Maps API: {e}")
        logging.error(f"Network error in Azure Maps API call: {e}")
        return []

# Page configuration
st.set_page_config(
    page_title="SafeChild - NGO/Admin Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🛡️",
)

# Custom CSS styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .case-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .urgent-case {
        border-left: 4px solid #dc3545;
    }
    .normal-case {
        border-left: 4px solid #28a745;
    }
    .status-pending {
        background-color: #fff3cd;
        color: #856404;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    .status-verified {
        background-color: #d1ecf1;
        color: #0c5460;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    .status-resolved {
        background-color: #d4edda;
        color: #155724;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    .blacklisted-case {
        border: 2px solid #d9534f !important;
        box-shadow: 0 0 8px rgba(217, 83, 79, 0.2);
        background: #fff5f5;
    }
</style>
""", unsafe_allow_html=True)

def load_lottieurl(url):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

# Animated branding (optional)
lottie_coding = load_lottieurl("https://raw.githubusercontent.com/raesha-dev/SafeChild_Hackwhiz/main/safe_child.json")

# Header branding
st.markdown("""
<div class="main-header">
    <h1> SafeChild - NGO Dashboard</h1>
    <p>Child Safety Report Management System</p>
</div>
""", unsafe_allow_html=True)

# Session state for UI sync
if "reset" not in st.session_state:
    st.session_state.reset = False
if "data_updated" not in st.session_state:
    st.session_state.data_updated = False

def clear_form():
    for k in ["status_filter", "urgency_filter", "location_coords"]:
        if k in st.session_state:
            del st.session_state[k]
    st.session_state.data_updated = True

# Sidebar - search, filters, animation
with st.sidebar:
    st.header("🔍 Filters")
    st.markdown("---")
    status_filter = st.selectbox(
        "Filter by Status",
        ["All", "Pending", "Verified", "Resolved"],
        key="status_filter"
    )
    urgency_filter = st.selectbox(
        "Filter by Urgency",
        ["All", "Normal", "Urgent"],
        key="urgency_filter"
    )
    if st.button("🔄 Reset Filters", use_container_width=True):
        clear_form()
        rerun()

    st.markdown("---")

    if lottie_coding:
        st_lottie(lottie_coding, height=200, key="coding")

    place_query = st.text_input("Enter location name to search", key="location_search_input")
    if place_query:
        candidates = azure_maps_search_place(place_query)
        if candidates:
            place_options = [
                f"{c['address'].get('freeformAddress', '')}, {c['address'].get('municipality', '')}, {c['address'].get('countrySubdivision', '')}" for c in candidates
            ]
            selected_place_str = st.selectbox("Select exact location", place_options, key="location_select_box")
            selected_idx = place_options.index(selected_place_str)
            selected_place = candidates[selected_idx]
            st.session_state['location_entityId'] = selected_place['entityId']
            st.session_state['location_coords'] = selected_place['position']
            st.markdown(f"Selected Coordinates: {selected_place['position']}")
        else:
            st.warning("No places found matching the input.")
    else:
        st.session_state['location_coords'] = None

# Handle session updates
if st.session_state.data_updated:
    st.session_state.data_updated = False

location_coords = st.session_state.get('location_coords', None)
status_filter = st.session_state.get('status_filter', "All")
urgency_filter = st.session_state.get('urgency_filter', "All")

reports = get_reports(status_filter, urgency_filter, location_coords)
blacklisted_locations = get_blacklisted_locations(threshold=3)

# Annotate reports with blacklist flag
filtered_reports = []
for r in reports:
    location = r[5] if len(r) > 5 else None
    is_blacklisted = location in blacklisted_locations
    filtered_reports.append((r, is_blacklisted))

if filtered_reports:
    total_cases = len(filtered_reports)
    pending_cases = len([r for r, _ in filtered_reports if r[3] == "Pending"])
    verified_cases = len([r for r, _ in filtered_reports if r[3] == "Verified"])
    resolved_cases = len([r for r, _ in filtered_reports if r[3] == "Resolved"])
    urgent_cases = len([r for r, _ in filtered_reports if r[4] == "Urgent"])

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(label="📊 Total Cases", value=total_cases)
    with col2:
        st.metric(label="⏳ Pending", value=pending_cases)
    with col3:
        st.metric(label="✅ Verified", value=verified_cases)
    with col4:
        st.metric(label="🎯 Resolved", value=resolved_cases)
    with col5:
        st.metric(label="🚨 Urgent", value=urgent_cases)

    st.markdown("---")
    left_col, right_col = st.columns([2, 1])

    with left_col:
        st.subheader("📋 Case Management")
        for r, is_blacklisted in filtered_reports:
            urgency_class = "urgent-case" if r[4] == "Urgent" else "normal-case"
            status_class = f"status-{r[3].lower()}"
            blacklist_class = "blacklisted-case" if is_blacklisted else ""
            with st.container():
                st.markdown(f"""
                <div class="case-card {urgency_class} {blacklist_class}">
                    <h4>Case ID {r[0]}</h4>
                    <div style="margin: 1rem 0;">
                        <strong>📱 Helpline:</strong> {r[1]}<br>
                        <strong>📝 Report:</strong> {r[2]}<br>
                        <strong>🚦 Urgency:</strong> <span style="background: {'#ffebee' if r[4] == "Urgent" else '#e8f5e8'}; padding: 2px 8px; border-radius: 4px; color: {'#c62828' if r[4] == "Urgent" else '#2e7d32'};">{r[4]}</span><br>
                        <strong>📌 Status:</strong> <span class="{status_class}">{r[3]}</span><br>
                        <strong>🌍 Location:</strong> {r[5]}<br>
                        <strong>⏰ Time:</strong> {r[6] if len(r)>6 else 'N/A'}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if is_blacklisted:
                    st.warning(f"⚠️ Report from blacklisted location: {r[5]}")

                try:
                    translated_text = translate_text(r[2])
                except Exception as e:
                    translated_text = "[Translation failed]"
                    st.warning(f"Translation error: {e}")
                st.markdown(f"**Translated Report:** {translated_text}")

                try:
                    key_phrases, sentiment = analyze_text_entities(translated_text)
                    st.markdown(f"**Sentiment:** {sentiment}")
                    st.markdown(f"**Key Phrases:** {', '.join(key_phrases) if key_phrases else 'None'}")
                except Exception as e:
                    st.warning(f"Analysis failed: {e}")

                col_status, col_button = st.columns([2, 1])
                with col_status:
                    new_status = st.selectbox(
                        f"Update Status for Case {r[0]}",
                        ["Pending", "Verified", "Resolved"],
                        index=["Pending", "Verified", "Resolved"].index(r[3]),
                        key=f"status_{r[0]}"
                    )
                with col_button:
                    st.write("")
                    st.write("")
                    if st.button(f"Update", key=f"btn_{r[0]}", use_container_width=True):
                        update_status(r[0], new_status)
                        st.success(f"✅ Case {r[0]} updated to {new_status}")
                        st.session_state.data_updated = True
                        rerun()
                st.markdown("---")

    with right_col:
        st.subheader("🗺️ Cases Map")
        latitudes = [r[6] for r, _ in filtered_reports if len(r) > 6 and r[6] is not None]
        longitudes = [r[7] for r, _ in filtered_reports if len(r) > 7 and r[7] is not None]
        if latitudes and longitudes:
            center_lat = sum(latitudes) / len(latitudes)
            center_lon = sum(longitudes) / len(longitudes)
        else:
            center_lat, center_lon = 12.91, 74.85  # Default to Mangalore

        m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles='OpenStreetMap')
        markers_added = 0
        for r, is_blacklisted in filtered_reports:
            if len(r) > 7:
                lat = r[6]
                lon = r[7]
                if lat is not None and lon is not None:
                    try:
                        marker_color = "blue"
                        if r[4] == "Urgent":
                            marker_color = "red"
                        elif r[3] == "Resolved":
                            marker_color = "green"
                        elif r[3] == "Verified":
                            marker_color = "orange"
                        if is_blacklisted:
                            marker_color = "black"
                        popup_content = f"""
                        <div style="width: 200px;">
                            <h4>Case {r[0]}</h4>
                            <p><strong>Status:</strong> {r[3]}</p>
                            <p><strong>Urgency:</strong> {r[4]}</p>
                            <p><strong>Time:</strong> {r[6] if len(r)>6 else 'N/A'}</p>
                            <p><strong>Report:</strong> {r[2][:100]}...</p>
                        </div>
                        """
                        folium.Marker(
                            [lat, lon],
                            popup=folium.Popup(popup_content, max_width=250),
                            tooltip=f"Case {r[0]} - {r[4]} ({r[3]})",
                            icon=folium.Icon(color=marker_color, icon='info-sign')
                        ).add_to(m)
                        markers_added += 1
                    except Exception as e:
                        st.error(f"Error processing location for Case {r[0]}: {str(e)}")

        if markers_added > 0:
            st_data = st_folium(m, width=700, height=500, returned_objects=["last_clicked"])
            st.info(f"📍 Showing {markers_added} cases on map")
            st.markdown("""
            **Map Legend:**
            - 🔴 Red: Urgent cases
            - 🟠 Orange: Verified cases  
            - 🟢 Green: Resolved cases
            - 🔵 Blue: Normal pending cases
            
            """)
        else:
            st.warning("No cases with valid location data to display on map")
            st_data = st_folium(m, width=700, height=500)

else:
    st.info("🔍 No reports found with current filters")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("""
        ### 📋 No Cases Available
        Try adjusting your filters or check back later for new reports.
        """)
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.session_state.data_updated = True
            rerun()
    with col2:
        default_map = folium.Map(location=[12.91, 74.85], zoom_start=12)
        st_folium(default_map, width=700, height=400)

# Footer branding
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>🛡️ SafeChild NGO Dashboard - Protecting Children, Building Safer Communities</p>
    <p>Mangalore Region | Emergency Helpline: +91-XXXX-XXXXX</p>
</div>
""", unsafe_allow_html=True)

if st.session_state.data_updated:
    st.session_state.data_updated = False
    rerun()
