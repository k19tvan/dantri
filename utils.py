from bs4 import BeautifulSoup
import requests
import asyncio
import aiohttp
import random
import httpx

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
            metadata = {
                'images': [img['src'] for img in container.find_all('img') if img.get('src')],
                'audios': [audio['src'] for audio in container.find_all('audio') if audio.get('src')],
                'videos': [video['src'] for video in container.find_all('video') if video.get('src')],
                'links': [a['href'] for a in container.find_all('a') if a.get('href')]
            }
            return PAGE(url, title.text, content, metadata)
    
    return PAGE("", "", "", "")

async def process_urls(urls):
    async with httpx.AsyncClient() as client:
        tasks = [process_url(client, url) for url in urls]
        return await asyncio.gather(*tasks)


    