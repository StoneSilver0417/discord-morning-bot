import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

def debug_naver_news(keyword):
    url = f"https://search.naver.com/search.naver?where=news&query={requests.utils.quote(keyword)}&sort=1"
    resp = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Save a snippet of the HTML to inspect
    with open("scratch/naver_news_snippet.html", "w", encoding="utf-8") as f:
        f.write(resp.text[:10000]) # First 10k chars
    
    print("Saved HTML snippet to scratch/naver_news_snippet.html")

if __name__ == "__main__":
    debug_naver_news("공무원")
