import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

def debug_finance_news():
    url = "https://finance.naver.com/news/mainnews.naver"
    print(f"Checking Finance News: {url}")
    resp = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Check common tags for titles on this specific page
    items = soup.select("dd.articleSubject a, a.articleSubject, .main_news_list a")
    print(f"Found {len(items)} items with specific selectors")
    for i, item in enumerate(items[:5]):
        print(f"  {i+1}. {item.get_text(strip=True)}")
    
    # Print all links that look like news titles
    all_links = soup.find_all('a')
    news_links = [l for l in all_links if "article_id" in l.get('href', '')]
    print(f"Found {len(news_links)} links containing 'article_id'")
    for i, l in enumerate(news_links[:10]):
        print(f"  {i+1}. {l.get_text(strip=True)[:50]}")

if __name__ == "__main__":
    debug_finance_news()
