import asyncio
import json
import os
from utils import *
from pathlib import Path


""" Get Links From All Timelines -> Process Urls"""
    
async def main():
    
    base_url = "https://dantri.com.vn/"
    list_categories = get_categories(base_url)
    
    for parent_name, list_childs in list_categories.items():
        for child in list_childs:
            
            category_url = "/".join(child[1].split("/")[-2:]).replace(".htm", "")      
            main_url = "https://dantri.com.vn/" + category_url + "/from/2024-{0}-{1}/to/2024-{2}-{3}/trang-{4}.htm"
            
            print(f"Crawling: {category_url}")
            
            # Get links from all pages of categories
            saved_links_path = Path(f"saved_links/{category_url}")
            saved_links_path.mkdir(parents=True, exist_ok=True)

            links = []
            
            if os.path.exists(saved_links_path/Path("Links.json")):
                with open(saved_links_path/Path("Links.json"), "r") as f:
                    links = json.load(f)
            
            else:
                dates = get_dates(main_url.format("{0}", "{1}", "{2}", "{3}", 30), main_url)
                links = await get_link_page_in_all_timelines(dates, main_url)
                with open(saved_links_path/Path("Links.json"), "w") as f:
                    json.dump(links, f, indent=4)

            print("Number of links crawled:", len(links))

            # Crawl
            N_links = 200
            print(f"Number of links used: {N_links}")
            pages = await process_urls(links[0:N_links])

            saved_path = Path("output"/Path(category_url))
            saved_path.mkdir(parents=True, exist_ok=True)
            
            cur_saved_path = saved_path/Path("run" + str(file_counts(saved_path) + 1))
            cur_saved_path.mkdir(parents=True, exist_ok=True)
            
            i = 0
            for page in pages: 
                if page.title: page.save(cur_saved_path/Path(str(i)+".json"))
                i += 1

asyncio.run(main())
