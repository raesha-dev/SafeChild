import streamlit as st
from cosmos_Utils import initialize_db, save_report, get_reports
from azure_cognitive_integration import speech_to_text, translate_text, analyze_text_entities
import os

st.set_page_config(page_title="SafeChild - Child Safety Reporting", layout="wide")

# Initialize DB at app start
initialize_db()

st.title("SafeChild - Child Safety Reporting Portal")

# Simple prank detection helper - matches common prank words (case insensitive)
def detect_prank(message):
    prank_keywords = ["lol", "prank", "fake", "joke"]
    return any(word in message.lower() for word in prank_keywords)

# Input form fields
phone = st.text_input("Helpline Number", value="1098")
message = st.text_area("Enter your message")
urgency = st.selectbox("Urgency level", ["Normal", "Urgent"])
location = st.text_input("Location (City/Village or lat,long)", value="Mangalore, India")

if st.button("Submit Report"):
    if not message.strip():
        st.warning("Please enter a message before submitting.")
    elif detect_prank(message):
        st.error("This message seems like a prank. Not saved.")
    else:
        try:
            # Step 1: Save plaintext report immediately for persistence
            # Save with latitude and longitude as None here; geocoding can be added to update these later
            save_report(phone, message, urgency, "Pending", location)

            # Step 2: Process with speech-to-text if audio available (assume text input, skipped here)
            # (If voice support is needed, an audio uploader can be added and speech_to_text called)

            # Step 3: Translate text to English for standardized analysis
            translated_msg = translate_text(message)

            # Step 4: Analyze translated text with text analytics to extract key phrases and detect sentiment
            key_phrases, sentiment = analyze_text_entities(translated_msg)

            # Step 5: Optionally update report in DB with analysis results or raise flags to admin
            # For simplicity, just show analysis results here:
            st.success("Report submitted successfully!")
            st.markdown(f"**Translated message:** {translated_msg}")
            st.markdown(f"**Key phrases:** {', '.join(key_phrases)}")
            st.markdown(f"**Sentiment detected:** {sentiment}")

        except Exception as e:
            st.error(f"An error occurred processing the report: {e}")

# Optional: Show previous reports for testing/debugging
st.markdown("---")
st.subheader("Recent Reports")
reports = get_reports()
for r in reports[:10]:  # Show the 10 most recent reports
    st.write(f"ID: {r[0]} | Phone: {r[1]} | Urgency: {r[4]} | Status: {r[3]} | Location: {r[5]} | Message: {r[2]}")
