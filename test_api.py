import google.generativeai as genai
from config.settings import GEMINI_API_KEY

print("កំពុងភ្ជាប់ទៅកាន់ Google API...")
genai.configure(api_key=GEMINI_API_KEY)

print("បញ្ជី Model ដែល API Key របស់អ្នកអាចប្រើបាន (សម្រាប់ Chat):")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ {m.name}")
except Exception as e:
    print(f"មានបញ្ហា: {e}")