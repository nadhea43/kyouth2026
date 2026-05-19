import os
import sys
import requests


GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "your-api-key-here")

OLLAMA_MODELS = {"llama3.1", "phi3", "deepseek-r1:1.5b"}
GEMINI_MODELS = {"gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3-flash-preview"}

def prompt_model(model:str, prompt:str) -> str:
    try:
        # use Ollama AI
        if model in OLLAMA_MODELS:
            # panggil Ollama from local
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model" : model, "prompt" :prompt, "stream" :False},
                timeout=120
            )
            data = response.json()
            # error handling
            if "error" in data:
                return f"[Ollama error] {data['error']}"
            return data.get("response", f"[No response] Full reply: {data}")
        # Use Gemini AI    
        elif model in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GOOGLE_API_KEY}"
            # calling Gemini
            response = requests.post(url, json={"contents" : [{"parts" : [{"text" : prompt}]}]})
            data = response.json()
            # error handling
            if "error" in data:
                return f"[Gemini Error] {data['error']['code']} {data['error']['status']}.{data['error']}"
            return data["candidates"][0]["content"]["parts"][0]["text"]
        
        else:
            
            return f"[Error] Unknown model : {model}"
        
    except Exception as e:
        return f"[Unexpected Error] {e}"
    

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        model = sys.argv[1]
        prompt = sys.argv[2]
    else:
        model = "llama3.1"
        prompt = "Say Hello"
    
    response = prompt_model(model,prompt)
    print("-------RESPONSE---------")
    print(response)

