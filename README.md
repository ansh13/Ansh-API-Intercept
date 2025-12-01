**Install Dependencies:**

pip install pan-aisecurity 
pip install google.genai 
pip install streamlit 


**Generate Gemini API key**
export GEMINI_API_KEY = 'key-value'

https://aistudio.google.com/u/1/api-keys

***Copy the API Key and change it in API_Intercept.py**


**On MAC:**
export GEMINI_API_KEY='key-value'
export PAN_API_KEY='key-value'

**On Windows**
$env:PAN_API_KEY = ''
$env:GEMINI_API_KEY = ''

**Run the app**

python -m streamlit run APP.py
