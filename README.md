**Install Dependencies:**

pip install pan-aisecurity 
pip install google.genai 
pip install streamlit 

***Copy the API Key and change it in API_Intercept.py**

export PANW_AI_SEC_API_KEY ='key-value'

**Generate Gemini API key**

https://aistudio.google.com/u/1/api-keys
and place the key on same path where scrypts are:
**On MAC:**
export GEMINI_API_KEY='key-value'
**On Windows**
set GEMINI_API_KEY='key-value'

**Run the app**

python -m streamlit run APP.py
