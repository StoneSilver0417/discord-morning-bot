import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

def debug_dust():
    url = "https://search.naver.com/search.naver?query=경산 중방동 날씨"
    resp = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    dust_chart = soup.select("li.item_today")
    print(f"Found {len(dust_chart)} items with 'li.item_today'")
    for i, item in enumerate(dust_chart):
        print(f"Item {i}: {item.get_text(separator=' | ', strip=True)}")

if __name__ == "__main__":
    debug_dust()
