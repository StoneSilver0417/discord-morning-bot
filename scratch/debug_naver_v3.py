import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

def debug_naver_news(keyword):
    url = f"https://search.naver.com/search.naver?where=news&query={requests.utils.quote(keyword)}&sort=1"
    resp = requests.get(url, headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Look for all <a> tags that have a title or look like a headline
    all_links = soup.find_all('a')
    print(f"Total links: {len(all_links)}")
    
    # Try to find common patterns for news titles in Naver
    # 1. news_tit
    # 2. _sp_each_title
    # 3. tit_main
    
    potential_titles = soup.find_all('a', class_=re.compile(r'tit|headline|subject'))
    print(f"Found {len(potential_titles)} potential titles with class regex 'tit|headline|subject'")
    for i, t in enumerate(potential_titles[:10]):
        print(f"  {i+1}. Class: {t.get('class')}, Text: {t.get_text(strip=True)[:50]}")

    # If nothing found, print all links with more than 10 characters text
    if not potential_titles:
        print("Printing links with > 20 chars text:")
        long_links = [l for l in all_links if len(l.get_text(strip=True)) > 20]
        for i, l in enumerate(long_links[:20]):
            print(f"  {i+1}. Class: {l.get('class')}, Text: {l.get_text(strip=True)[:50]}")

if __name__ == "__main__":
    debug_naver_news("공무원")
