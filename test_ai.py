import sys
import tomllib
from PIL import Image
from google import genai
from core import MODEL, extract_name

key = tomllib.load(open(".streamlit/secrets.toml", "rb"))["GEMINI_API_KEY"]
client = genai.Client(api_key=key)

print("Trying model:", MODEL)
img = Image.open(sys.argv[1])
try:
    print("RESULT:", extract_name(client, img, MODEL))
except Exception as e:
    print("ERROR:", e)