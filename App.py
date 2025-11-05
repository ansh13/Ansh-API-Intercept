# app.py

import streamlit as st
import json
from API_ansh import run_secure_llm_pipeline  # Import your pipeline function

# --- Streamlit App Configuration ---
st.set_page_config(page_title="Secure LLM Gateway", layout="wide")

# --- Streamlit Frontend ---

st.title("🛡️ Secure LLM Gateway (Gemini + PAN AISecurity)")
st.caption("Enter a prompt below. Your input and the AI's response will be checked against Palo Alto Networks AI Security profiles.")

# Text area for user input
user_prompt = st.text_area("Enter your prompt here:", height=150)

# Button to submit the prompt
if st.button("Run Secure Query"):
    if user_prompt:
        with st.spinner("Running secure LLM pipeline..."):
            # Execute your core logic function with the user's input
            result = run_secure_llm_pipeline(user_prompt)

        # --- Display Results ---
        
        st.subheader("Final Response:")
        
        if result['status'] == "success":
            st.success("Query successful and safe.")
            st.markdown(f"**AI Response:**")
            st.info(result['final_response'])
            
        elif result['status'] == "blocked_prompt":
            st.error(f"🚨 PROMPT BLOCKED by Inbound Security Check.")
            st.warning(f"Reason: {result['reason']}")
            
        elif result['status'] == "blocked_response":
            st.error("🛑 RESPONSE BLOCKED by Outbound Security Check.")
            st.warning("The AI generated content that violated a security policy and was filtered.")
            
        else:
            st.exception(result.get('message', 'An unknown error occurred during execution.'))

    else:
        st.warning("Please enter a prompt to run the query.")