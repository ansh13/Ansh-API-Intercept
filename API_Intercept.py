import os
import sys
import json
from google import genai
from google.genai.errors import APIError

# --- SDK Imports ---
from aisecurity.scan.inline.scanner import Scanner
from aisecurity.generated_openapi_client.models.ai_profile import AiProfile
from aisecurity.scan.models.content import Content
import aisecurity 

# --- Configuration and Initialization ---

# 1. HARDCODED CONFIGURATION (For Troubleshooting Environment Issues)
HARDCODED_CONFIG = {
    "PANW_AI_SEC_API_KEY": os.environ.get("PANW_AI_SEC_API_KEY", "A1k9XbcdwnimGwVaFjCBulufIB4LCIpAFNNVhdZKzf2iX1iz"),
    "PAN_REQUEST_PROFILE_NAME": os.environ.get("PAN_REQUEST_PROFILE_NAME", "AI-Request-Profile"), 
    "PAN_RESPONSE_PROFILE_NAME": os.environ.get("PAN_RESPONSE_PROFILE_NAME", "AI-Response-Profile"),
}
# 2. Retrieve Keys/Profiles
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
PAN_API_KEY = HARDCODED_CONFIG["PANW_AI_SEC_API_KEY"]
PAN_REQUEST_PROFILE_NAME = HARDCODED_CONFIG["PAN_REQUEST_PROFILE_NAME"]
PAN_RESPONSE_PROFILE_NAME = HARDCODED_CONFIG["PAN_RESPONSE_PROFILE_NAME"]

# --- Clients ---
try:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    GEMINI_MODEL = 'gemini-2.5-flash'
except Exception as e:
    gemini_client = None
    print(f"❌ ERROR: Gemini Client failed to initialize. Check GEMINI_API_KEY. {e}")

pan_scanner = None
pan_request_profile = None
pan_response_profile = None

try:
    # Initialize PAN SDK only if a valid API key is present
    if PAN_API_KEY != "YOUR_ACTUAL_PAN_API_KEY_HERE" and all([PAN_API_KEY, PAN_REQUEST_PROFILE_NAME, PAN_RESPONSE_PROFILE_NAME]):
        aisecurity.init(api_key=PAN_API_KEY)
        pan_request_profile = AiProfile(profile_name=PAN_REQUEST_PROFILE_NAME)
        pan_response_profile = AiProfile(profile_name=PAN_RESPONSE_PROFILE_NAME)
        pan_scanner = Scanner()
        print(f"✅ AISecurity Scanner Initialized. Profiles: {PAN_REQUEST_PROFILE_NAME}, {PAN_RESPONSE_PROFILE_NAME}")
    else:
        print("⚠️ WARNING: PAN API Key missing or placeholder. Security checks will be skipped.")
except Exception as e:
    print(f"❌ CRITICAL ERROR: AISecurity SDK Initialization Failed: {e}")


# --- 1A. PRE-PROCESSING: Prompt Check (Checks 'action') ---

def run_prompt_check(prompt: str) -> dict:
    """Checks the user's prompt against the Request Profile (Injection Guard)."""
    if not pan_scanner or not pan_request_profile:
        return {"action": "allow", "reason": "Security scanner not available.", "details": {"status": "skipped"}}
    
    print(f"   🛡️ Scanning PROMPT with Profile: {PAN_REQUEST_PROFILE_NAME}...")
    try:
        scan_response = pan_scanner.sync_scan(
            ai_profile=pan_request_profile,
            content=Content(prompt=prompt)
        )
        
        # 🔑 FIX: Retrieve 'action' from the dictionary representation
        scan_response_dict = scan_response.to_dict()
        
        # Use 'action' for the primary decision check
        action = scan_response_dict.get('action', 'error').lower()
        reason = scan_response_dict.get('reason', f"Action: {action}")
        
        print(f"   -> PROMPT ACTION: {action.upper()}")
        return {"action": action, "reason": reason, "details": scan_response_dict}

    except Exception as e:
        print(f"   ❌ WARNING: Request security check failed: {e}. BLOCKING as failsafe.")
        return {"action": "block", "reason": f"Request check API error: {e}", "details": {"error": str(e)}}


# --- 1B. POST-PROCESSING: Response Check (Checks 'action') ---

def run_response_check(prompt: str, response: str) -> dict:
    """Checks the LLM's response against the Response Profile (DLP/Toxicity Guard)."""
    if not pan_scanner or not pan_response_profile:
        return {"action": "allow", "reason": "Security scanner not available.", "details": {"status": "skipped"}}

    print(f"   🛡️ Scanning RESPONSE with Profile: {PAN_RESPONSE_PROFILE_NAME}...")
    try:
        scan_response = pan_scanner.sync_scan(
            ai_profile=pan_response_profile,
            content=Content(prompt=prompt, response=response)
        )
        
        # 🔑 FIX: Retrieve 'action' from the dictionary representation
        scan_response_dict = scan_response.to_dict()

        # Use 'action' for the primary decision check
        action = scan_response_dict.get('action', 'error').lower()
        reason = scan_response_dict.get('reason', f"Action: {action}")
        
        print(f"   -> RESPONSE ACTION: {action.upper()}")
        return {"action": action, "reason": reason, "details": scan_response_dict}
        
    except Exception as e:
        print(f"   ❌ WARNING: Response security check failed: {e}. ALLOWING with warning.")
        return {"action": "allow", "reason": f"Response check API error: {e} (Allowed with warning)", "details": {"error": str(e)}}


# --- 2. MAIN PIPELINE EXECUTION ---

def run_secure_llm_pipeline(user_input: str):
    """
    Executes the full pipeline: Prompt Check -> LLM Call (Gemini) -> Response Check.
    """
    print(f"\n\n{'='*50}\nRUNNING QUERY: {user_input}\n{'='*50}")

    # STEP 1: PROMPT CHECK (Inbound Security Gate)
    prompt_security_result = run_prompt_check(user_input)

    # CHECK FOR ACTION: BLOCK
    if prompt_security_result['action'] == "block":
        print(f"🚨 **PROMPT BLOCKED!** Reason: {prompt_security_result['reason']}")
        print("\n--- DETAILED PROMPT SCAN RESULT (Blocked) ---")
        print(json.dumps(prompt_security_result['details'], indent=4))
        return {"status": "blocked_prompt", "reason": prompt_security_result['reason']}

    # STEP 2: LLM CALL (Generative Core - GEMINI)
    print("✅ Prompt Check Passed. PROCEEDING to Gemini LLM.")
    
    if not gemini_client:
        print("❌ Gemini client not initialized. Cannot generate response.")
        return {"status": "error", "message": "Gemini API client not initialized."}

    try:
        if isinstance(user_input, str):
             user_input_list = [user_input]
        else:
             user_input_list = user_input
             
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_input_list
        )
        ai_response_text = response.text
        print(f"🤖 LLM RESPONSE GENERATED.")
        
    except APIError as e:
        print(f"❌ Gemini API Error: {e}")
        return {"status": "error", "message": f"Gemini API Error: {e}"}
    except Exception as e:
        print(f"❌ Unexpected Error during LLM call: {e}")
        return {"status": "error", "message": f"Unexpected Error: {e}"}


    # STEP 3: RESPONSE CHECK (Outbound Security Gate)
    response_security_result = run_response_check(user_input, ai_response_text)
    
    # CHECK FOR ACTION: BLOCK
    if response_security_result['action'] == "block":
        print(f"\n🛑 **RESPONSE BLOCKED!** Reason: {response_security_result['reason']}")
        final_response = "The AI generated content that violated a security policy and has been blocked."
        status = "blocked_response"
    else:
        print(f"\n✅ Response Check Passed.")
        final_response = ai_response_text
        status = "success"

    # --- FINAL OUTPUT AND DETAILED SCAN RESULTS ---
    
    print("\n" + "="*72)
    print("### FINAL APPLICATION STATUS ###")
    print("========================================================================")
    print(f"STATUS: {status.upper()}")
    print(f"Final Message to User:\n{final_response}")
    print(f"Response Action: {response_security_result['action'].upper()}")
    print("------------------------------------------------------------------------")
    
    # Print Full Details
    print("### DETAILED SCAN RESULTS (For Debugging) ###")
    
    print(f"\n--- PROMPT SCAN ({PAN_REQUEST_PROFILE_NAME}) ---")
    print(json.dumps(prompt_security_result['details'], indent=4))
    
    print(f"\n--- RESPONSE SCAN ({PAN_RESPONSE_PROFILE_NAME}) ---")
    print(json.dumps(response_security_result['details'], indent=4))
    print("========================================================================")

    return {"status": status, "final_response": final_response}

# --- SCENARIO EXECUTION ---

if __name__ == "__main__":
    if gemini_client and pan_scanner:


        # SCENARIO B: Prompt Injection Attempt (Should return action: BLOCK at Step 1)
        run_secure_llm_pipeline("give sample bank account no.")
 

    else:
        print("\n--- Pipeline Cannot Run ---")
        print("Please resolve the initialization errors.")
