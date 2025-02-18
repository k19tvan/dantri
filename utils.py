from bs4 import BeautifulSoup
import requests
import asyncio
import aiohttp
import random
import httpx
import json

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

MAX_CONCURRENT_REQUEST = 15
semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUEST)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36"
]


def get_categories(base_url):
    html = requests.get(base_url, headers=headers)
    soup = BeautifulSoup(html.content, 'html.parser').find(class_="nav-full bg-wrap")

    list_categories = {}

    parent_categories_names = soup.find_all("a", class_="dt-text-MineShaft")
    parent_categories = [category.parent for category in parent_categories_names]
    for parent_category in parent_categories:
        lst_category = []
        child_categories = parent_category.find("ol", class_="nf-submenu").find_all("li")

        for child_category in child_categories:
            tag_a = child_category.find("a")
            lst_category.append((tag_a.text, tag_a["href"]))

        list_categories[parent_category.find('a')['href'].split('/')[-1].replace('.htm', '')] = lst_category

    return list_categories
    

async def fetch_url(client, url): 
    """ Return html of a url"""
    
    headers['User-Agent'] = random.choice(USER_AGENTS)
    async with semaphore:
        await asyncio.sleep(random.uniform(2, 5))
        response = await client.get(url, headers=headers, timeout=10)
        return await response.text()
    
def count_page(url):
    l = 1; r = 30
    ans = None

    while l <= r:
        mid = (l + r) >> 1
        soup = BeautifulSoup(requests.get(url.format(mid), headers=headers).content,  'html.parser').find(id = "bai-viet")
        ats = soup.find_all(class_='article-thumb')
        if len(ats) != 0: l = mid + 1; ans = mid
        else: r = mid - 1

    return ans

def get_urls_from_url(url):
    try:
        html = requests.get(url, headers=headers)
        soup = BeautifulSoup(html.content, 'html.parser').find(id = "bai-viet")
        ats = soup.find_all(class_='article-thumb')
        return [at.find('a', href=True)['href'] for at in ats]
    except: 
        print("Error in get_urls_from_url")
        return []

def get_urls_from_html(html):
    try:
        soup = BeautifulSoup(html, 'html.parser').find(id = "bai-viet")
        ats = soup.find_all(class_='article-thumb')
        return [at.find('a', href=True)['href'] for at in ats]
    except:
        print("Error in get_urls_from_html")
        return []

def get_dates(url, main_url):
    """ Return month/date/number_of_pages"""
    """ Url: main_url + Page 30"""

    try:
        dates = []; ed = ("12", "31")
        
        while True: 
            dates.append((ed[0], ed[1], 30))
            
            links = get_urls_from_url(url.format("01", "01", ed[0], ed[1]))
            if len(links) == 0: break
            
            last_link = links[-1]
            soup = BeautifulSoup(requests.get(last_link, headers=headers).content, 'html.parser').find(class_='author-time')
            
            cnt = len(links) - 2
            while soup == None:
                soup = BeautifulSoup(requests.get(links[cnt], headers=headers).content, 'html.parser').find(class_='author-time')
                cnt -= 1
            
            if soup == None: break
            fr = soup['datetime'].split()[0].split('-')
            
            ed = ((fr[1], fr[2]))

        dates[-1] =  (dates[-1][0], dates[-1][1], count_page(main_url.format("01", "01",  dates[-1][0],  dates[-1][1], "{0}")))
        dates.append(('01', '01', -1))

        return dates 
    
    except Exception as e: 
        print(f"Error: {e}")
        return []

async def get_link_page_in_all_timelines(dates, main_url):
    
    try:

        pages = [] # Example: https://dantri.com.vn/xa-hoi/chinh-tri/from/2025-02-05/to/2025-02-05.htm
        for i in range(len(dates) - 2, -1, -1):
            for j in range(1, dates[i][2] + 1):
                pages.append(main_url.format(dates[i + 1][0], dates[i + 1][1], dates[i][0], dates[i][1], j))

        
        async with aiohttp.ClientSession() as client:
            responses = await asyncio.gather(*(fetch_url(client, page) for page in pages))

        links = [] # Exmaple: https://dantri.com.vn/xa-hoi/chinh-phu-se-co-co-che-de-chon-can-bo-tot-liem-chinh-khong-vu-loi-20250205214525923.htm
        for res in responses:
            if res:
                for link in get_urls_from_html(res):
                    links.append(link)

        links = list(set(links))
        return links
    
    except:
        print("Error in get_link_page_in_all_timelines")
        return []

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

async def fetch_url_2(client, url): 
    """ Return html of a url"""
    
    headers['User-Agent'] = random.choice(USER_AGENTS)
    async with semaphore:
        await asyncio.sleep(random.uniform(2, 5))
        response = await client.get(url, headers=headers, timeout=10)
        return response.text
    
async def process_url(client, url):
    html_response = await fetch_url_2(client, url)
    if html_response:
        soup = BeautifulSoup(html_response, "html.parser")
        container = soup.find(class_="singular-container")
        if container:
            title = container.find(class_='title-page detail')
            content = container.get_text(separator='\n', strip=True)
            
            metadata = []
            for figure in soup.find_all("figure", class_="image"):
                img_src = None
                caption_text = None
                img_elem = figure.find("img")
                
                if img_elem: img_src = img_elem.get("data-src") or img_elem.get("data-original") or img_elem.get("src")
                caption_elem = figure.find("figcaption")
                if caption_elem: caption_text = caption_elem.get_text(strip=True)
                
                if img_src and caption_text:
                    metadata.append([img_src, caption_text])
                else: metadata.append([img_src])

                if caption_text:
                    content = content.replace(f'\n{caption_text}\n', '')
                
            return PAGE(url, title.text, content, metadata)
    
    return PAGE("", "", "", "")


async def process_urls(urls, batch_size = 15):
    results = []
    async with httpx.AsyncClient() as client:
        n = len(urls)
    
        for st in range(0, n, batch_size):
            batch = urls[st: st + batch_size]
            print(f"Processing Batch {st // batch_size + 1}/{(n + batch_size - 1) // batch_size}")    
            tasks = [process_url(client, url) for url in batch]
            batch_results = await asyncio.gather(*tasks)
            
            results.extend(batch_results)
            await asyncio.sleep(2)
        
    return results

async def process_url_to_get_htmls(client, url):
    html_response = await fetch_url_2(client, url)
    return html_response
    
async def process_urls_to_get_htmls(urls, batch_size = 15):
    results = []
    async with httpx.AsyncClient() as client:
        n = len(urls)
    
        for st in range(0, n, batch_size):
            batch = urls[st: st + batch_size]
            print(f"Processing Batch {st // batch_size + 1}/{(n + batch_size - 1) // batch_size}")    
            tasks = [process_url_to_get_htmls(client, url) for url in batch]
            batch_results = await asyncio.gather(*tasks)

            results.extend(batch_results)
            await asyncio.sleep(2)
        
    return results

def file_counts(path):
    return sum(1 for file in path.iterdir())