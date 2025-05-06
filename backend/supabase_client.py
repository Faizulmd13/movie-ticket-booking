import os
from dotenv import load_dotenv
import requests

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def get_data(endpoint):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}?select=*"
    response = requests.get(url, headers=headers)
    return response.json()

def insert_data(endpoint, payload):
    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    response = requests.post(url, json=payload, headers=headers)
    return response.json()
