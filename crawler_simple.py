import asyncio
import json
import os
from utils import *
from pathlib import Path
import random


""" Get Links From All Timelines -> Process Urls"""
    
categories_used = ["giao-duc", "phap-luat", "the-thao", "giai-tri", "cong-nghe", "kinh-doanh", "the-gioi"]
    
async def main():
    
    base_url = "https://dantri.com.vn/"
    categories = get_categories(base_url)
    print(categories)
    categories = ['cong-nghe']

    for year in range(2022, 2023):
        print(f"Year: {year}")
        for parent_name in categories:
            # tmp
            # if parent_name == 'the-gioi':
            #     continue

            main_url = base_url + parent_name + "/from/" + str(year) + "-{0}-{1}/to/" + str(year) + "-{2}-{3}/trang-{4}.htm"
            category_short_name = parent_name
            
            if category_short_name not in categories_used: continue
            print(f"Crawling: {category_short_name}")
            
            # Get links from all pages of categories
            saved_links_path = Path(f"saved_links/{str(year)}/{category_short_name}")
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

            if len(links) == 0: continue
            
            # Crawl
            N_links = min(len(links), 1000)
            print(f"Number of links used: {N_links}")
            random_links = random.sample(links, N_links)
            pages = await process_urls(random_links)

            saved_path = Path("output")/Path(str(year))/Path(category_short_name)
            saved_path.mkdir(parents=True, exist_ok=True)
            
            cur_saved_path = saved_path/Path("run" + str(file_counts(saved_path) + 1))
            cur_saved_path.mkdir(parents=True, exist_ok=True)
            
            i = 0
            for page in pages: 
                if page.title: page.save(cur_saved_path/Path(str(i)+".json"))
                i += 1
                
            # crawl_html
            # N_links = min(len(links), 1000)
            # print(f"Number of links used: {N_links}")
            # random_links = random.sample(links, N_links)
            # htmls = await process_urls_to_get_htmls(random_links)
            #
            # saved_path = Path("output_html")/Path(str(year))/Path(category_short_name)
            # saved_path.mkdir(parents=True, exist_ok=True)
            #
            # cur_saved_path = saved_path/Path("run" + str(file_counts(saved_path) + 1))
            # cur_saved_path.mkdir(parents=True, exist_ok=True)
            #
            # i = 0
            # for i, html in enumerate(htmls):
            #     with open(cur_saved_path/Path(str(i)+".html"), "w", encoding="utf-8") as f:
            #         f.write(html)

asyncio.run(main())
