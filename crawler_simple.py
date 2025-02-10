import asyncio
import json
import os
from utils import *
from pathlib import Path

main_url = "https://dantri.com.vn/giao-duc/from/2024-{0}-{1}/to/2024-{2}-{3}/trang-{4}.htm"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36"
]

def get_dates(url):
    lst = []
    st = ("01", "01")
    ed = ("12", "31")
    
    while 1:
        links = get_urls(url.format(st[0], st[1], ed[0], ed[1]))
        if len(links) == 0: break
        tu = get_date_from_link(links[-1])
        lst.append((tu[0], tu[1], 30))
        ed = lst[-1]
    
    lst[-1] =(lst[-1][0], lst[-1][1], count_page(main_url.format(st[0], st[1], lst[-1][0], lst[-1][1], "{0}")))
    lst.append(('01', '01', 1))
    return lst

async def get_link_page_in_all_timelines(dates):
    links = []
    for i in range(len(dates) - 2, 0, -1):
        for j in range(1, dates[i][2] + 1):
            links.append(main_url.format(dates[i + 1][0], dates[i + 1][1], dates[i][0], dates[i][1], j))

    responses = await asyncio.gather(*(fetch_url(link) for link in links))
    
    links_page = []
    for res in responses:
        if res:
            for link in get_urls_from_html(res):
                links_page.append(link)

    links_page = list(set(links_page))
    
    print("Number of links crawled", len(links_page))
    return links_page
    
async def main():
    dates = get_dates(main_url.format("{0}", "{1}", "{2}", "{3}", 30))

    if os.path.exists("links.json"):
        with open("links.json", "r") as f:
            links = json.load(f)
    else:
        links = await get_link_page_in_all_timelines(dates)
        with open("links.json", "w") as f:
            json.dump(links, f, indent=4)

    print("Number of links crawled:", len(links))
    
    N_links = 2
    print(f"Number of links used: {N_links}")
    pages = await process_urls(links[0:N_links])

    saved_path = Path("output")
    saved_path.mkdir(parents=True, exist_ok=True)
    
    cur_saved_path = saved_path/Path("run" + str(file_counts(saved_path) + 1))
    cur_saved_path.mkdir(parents=True, exist_ok=True)
    
    for i, page in enumerate(pages): page.save(cur_saved_path/Path(str(i)+".json"))

asyncio.run(main())
