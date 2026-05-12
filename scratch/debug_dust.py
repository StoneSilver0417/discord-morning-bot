import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

def debug_dust():
    url = "https://search.naver.com/search.naver?query=경산 중방동 날씨"
    resp = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # 1. Check for dust info in the today chart
    dust_chart = soup.select("li.item_today")
    print(f"Found {len(dust_chart)} items with 'li.item_today'")
    for item in dust_chart:
        label = item.select_one("span.label")
        value = item.select_one("span.txt")
        if label and value:
            print(f"  {label.get_text(strip=True)}: {value.get_text(strip=True)}")

    # 2. Try alternate selectors
    if not dust_chart:
        print("Trying alternate: 'ul.today_chart_list li'")
        alt_chart = soup.select("ul.today_chart_list li")
        for item in alt_chart:
            print(f"  Item text: {item.get_text(separator=' ', strip=True)}")

if __name__ == "__main__":
    debug_dust()
