import streamlit as st
import speech_recognition as sr
import google.generativeai as genai

# Configure Gemini API
genai.configure(api_key="AIzaSyDdMi8XFsFo2ALx6VLa9YAAyViUpaM3rsU")

# Initialize recognizer
recognizer = sr.Recognizer()

# Streamlit UI
st.title("🎤 Voice Assistant with Gemini 1.5 Flash")
st.write("Speak your query and get a response!")

# Record and transcribe voice
if st.button("Start Listening"):
    with sr.Microphone() as source:
        st.info("Listening... Please speak now.")
        audio = recognizer.listen(source)

    try:
        # Convert speech to text
        user_query = recognizer.recognize_google(audio)
        st.success(f"You said: {user_query}")

        # Use Gemini 1.5 Flash model
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(user_query)

        # Display response
        st.subheader("🤖 Gemini's Response:")
        st.write(response.text)

    except sr.UnknownValueError:
        st.error("Sorry, could not understand your speech.")
    except sr.RequestError as e:
        st.error(f"Could not request results; {e}")