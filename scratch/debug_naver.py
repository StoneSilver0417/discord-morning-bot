import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

def debug_naver_news(keyword):
    url = f"https://search.naver.com/search.naver?where=news&query={requests.utils.quote(keyword)}&sort=1"
    print(f"Searching: {url}")
    resp = requests.get(url, headers=HEADERS)
    print(f"Status Code: {resp.status_code}")
    
    soup = BeautifulSoup(resp.text, "html.parser")
    # Check for the news titles
    titles = soup.select("a.news_tit")
    print(f"Found {len(titles)} titles with 'a.news_tit'")
    
    for i, title in enumerate(titles[:3]):
        print(f"  {i+1}. {title.get_text(strip=True)}")
    
    if len(titles) == 0:
        # Try finding any link that looks like a news title
        links = soup.find_all('a')
        news_links = [l for l in links if 'news' in l.get('href', '').lower()]
        print(f"Found {len(news_links)} links containing 'news' in href")
        # Print first few link texts and classes
        for l in links[:20]:
            print(f"  Class: {l.get('class')}, Text: {l.get_text(strip=True)[:30]}")

if __name__ == "__main__":
    debug_naver_news("공무원")
