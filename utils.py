from bs4 import BeautifulSoup
import requests
import asyncio
import aiohttp
import random
import httpx
import json
from pathlib import Path

async def async_aiohttp_get_all(urls):
    async with aiohttp.ClientSession() as session:
        async def fetch(url):
            async with session.get(url) as response:
                return await response.text()
        return await asyncio.gather(*[
            fetch(url) for url in urls
        ])

headers = {
    'Host':'dantri.com.vn',
    'Connection':'keep-alive',
    'Cache-Control':'max-age=0',
    'sec-ch-ua':'"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
    'sec-ch-ua-mobile':'?0',
    'sec-ch-ua-platform':'"Windows"',
    'Upgrade-Insecure-Requests':'1',
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Sec-Fetch-Site':'same-origin',
    'Sec-Fetch-Mode':'navigate',
    'Sec-Fetch-User':'?1',
    'Sec-Fetch-Dest':'document',
    'Accept-Encoding':'gzip, deflate, br, zstd',
    'Accept-Language':'en-US,en;q=0.9',
}

def count_page(url):
    l = 1; r = 30
    ans = None

    while l <= r:
        mid = (l + r) >> 1
        if check_page_valid(url, mid): l = mid + 1; ans = mid
        else: r = mid - 1

    return ans

def check_page_valid(url, num):
    soup = BeautifulSoup(requests.get(url.format(num), headers=headers, verify=False).content,  'html.parser').find(id = "bai-viet")
    ats = soup.find_all(class_='article-thumb')

    return len(ats) != 0


def get_urls(url):
    html = requests.get(url, headers=headers, verify=False)
    soup = BeautifulSoup(html.content, 'html.parser').find(id = "bai-viet")
    ats = soup.find_all(class_='article-thumb')

    return [at.find('a', href=True)['href'] for at in ats]

def get_urls_from_html(html):
    try:
        soup = BeautifulSoup(html, 'html.parser').find(id = "bai-viet")
        if soup == None: print(html)
        ats = soup.find_all(class_='article-thumb')
    except:
        f = open("fu.html", "a")
        f.write(html)
        f.close()
        return None
    return [at.find('a', href=True)['href'] for at in ats]

def get_date_from_link(url):
    soup = BeautifulSoup(requests.get(url, headers=headers, verify=False).content, 'html.parser').find(class_ = 'author-time')
    split = soup['datetime'].split()[0].split('-')
    return (split[1], split[2])

def file_counts(path):
    return sum(1 for file in path.iterdir())

class PAGE:
    def __init__(self, url, title, content, metadata):
        self.url = url
        self.title = title
        self.content = content
        self.metadata = metadata
        
    def show(self):
        print(f"Url: {self.url}")
        print(f"Title: {self.title}")
        print(f"Content: {self.content}")
        print(f"Metadata: {self.metadata}")
        
    def save(self, path):
        ans = {}
        ans['url'] = self.url
        ans['title'] = self.title
        ans['content'] = self.content
        ans['metadata'] = self.metadata
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ans, f, indent=4, ensure_ascii=False)

        

MAX_CONCURRENT_REQUEST = 3
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUEST)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36"
]

async def fetch_url(client, url):
    headers['User-Agent'] = random.choice(USER_AGENTS)
    async with semaphore:
        await asyncio.sleep(random.uniform(2, 5))
        response = await client.get(url, headers=headers, timeout=10)
        return response.text
    
async def process_url(client, url):
    html_response = await fetch_url(client, url)
    if html_response:
        soup = BeautifulSoup(html_response, "html.parser")
        container = soup.find(class_="singular-container")
        if container:
            title = container.find(class_='title-page detail')
            content = container.get_text(separator='\n', strip=True).replace("\n", "\\n")
            
            metadataraws = []
            for figure in soup.find_all("figure", class_="image align-center"):
                for elem in figure.find_all(["img", "figcaption"]):
                    if elem.name == "img":
                        src = elem.get("data-src") or elem.get("data-original") or elem.get("src")
                        if src and src.startswith("http"):
                            metadataraws.append(src)
                    elif elem.name == "figcaption":
                        metadataraws.append(elem.get_text(strip=True))
            
            
            metadata = []
            cur = []
            for metadataraw in metadataraws:
                cur.append(metadataraw)
                if not ("http" in metadataraw):
                    metadata.append(cur)
                    cur = [] 
                
            return PAGE(url, title.text, content, metadata)
    
    return PAGE("", "", "", "")

async def process_urls(urls):
    async with httpx.AsyncClient() as client:
        tasks = [process_url(client, url) for url in urls]
        return await asyncio.gather(*tasks)


    