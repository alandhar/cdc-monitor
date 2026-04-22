import requests
import os
from dotenv import load_dotenv

load_dotenv()

def data_weather(api_key):
    url = "https://api.tomorrow.io/v4/weather/forecast"
    params = {
        "location": "42.3478,-71.0466",
        "apikey": api_key
    }
    resp = requests.get(url=url, params=params)
    print(resp.json())


def main():
    TOMORROW_API_KEY = os.getenv("TOMORROW_API_KEY")
    data = data_weather(TOMORROW_API_KEY)

if __name__ == "__main__":
    main()