import tomllib
from google import genai

key = tomllib.load(open(".streamlit/secrets.toml", "rb"))["GEMINI_API_KEY"]
client = genai.Client(api_key=key)
for m in client.models.list():
    print(m.name)