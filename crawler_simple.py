import asyncio
import json
import os

from async_timeout import timeout

from utils import *
from pathlib import Path
import random


""" Get Links From All Timelines -> Process Urls"""
    
categories_used = ["giao-duc", "phap-luat", "the-thao", "giai-tri", "khoa-hoc-cong-nghe", "kinh-doanh", "the-gioi"]
    
async def main():
    
    base_url = "https://dantri.com.vn/"
    categories = get_categories(base_url)

    for year in range(2021, 2023):
        print(f"Year: {year}")
        for category in categories:
            main_url = category.replace(".htm", "") + "/from/" + str(year) + "-{0}-{1}/to/" + str(year) + "-{2}-{3}/trang-{4}.htm"
            category_short_name = str(category).split('/')[3].replace('.htm', '')
            
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
            N_links = min(len(links), 1000)
            print(f"Number of links used: {N_links}")
            random_links = random.sample(links, N_links)
            htmls = await process_urls_to_get_htmls(random_links)

            saved_path = Path("output_html")/Path(str(year))/Path(category_short_name)
            saved_path.mkdir(parents=True, exist_ok=True)
            
            cur_saved_path = saved_path/Path("run" + str(file_counts(saved_path) + 1))
            cur_saved_path.mkdir(parents=True, exist_ok=True)
            
            i = 0
            for i, html in enumerate(htmls): 
                with open(cur_saved_path/Path(str(i)+".html"), "w", encoding="utf-8") as f:
                    f.write(html)


import json
import requests
import os
from langchain_mistralai import ChatMistralAI
from langchain.schema import HumanMessage
import time

mistral_api_key = "Q5FexKRGA3tZ1XVuAWg2YuP0Xg5zQ0wQ"


# Define the JSON schema for structured output
json_schema = {
  "title": "ArticleExtractionSchema",
  "description": "Schema for extracting structured data from newspaper articles",
  "type": "object",
  "properties": {
    "url": {
      "type": "string",
      "description": "The URL of the article."
    },
    "title": {
      "type": "string",
      "description": "The title of the article."
    },
    "content": {
      "type": "string",
      "description": "The full text content of the article."
    },
    "metadata": {
      "type": "array",
      "description": "An array of image metadata.",
      "items": {
        "type": "array",
        "items": [
          {
            "type": "string",
            "description": "The URL of the image."
          },
          {
            "type": "string",
            "description": "The caption or description of the image."
          }
        ]
      }
    }
  },
  "required": ["url", "title", "content", "metadata"]
}

from pydantic import BaseModel, HttpUrl
from typing import List
import requests, json, time, asyncio
from langchain_core.messages import HumanMessage
from bs4 import BeautifulSoup

class MetadataItem(BaseModel):
  image_url: str  # The URL of the image.
  description: str  # The caption or description of the image.

class Article(BaseModel):
  url: str  # The URL of the article.
  title: str  # The title of the article.
  content: str  # The full text content of the article.
  metadata: List[MetadataItem]  # Image metadata list.

# Mistral AI setup
llm = ChatMistralAI(model="ministral-8b-2410", api_key=mistral_api_key, temperature=0.2, timeout=300)
structured_llm = llm.with_structured_output(Article, method='json_mode')


def fetch_html(url):
    """Fetch webpage HTML."""
    response = requests.get(url)
    return response.text if response.status_code == 200 else {"error": "Failed to fetch page"}


def extract_main_content(html_content):
    """Extract relevant content from HTML, prioritizing <main>."""
    soup = BeautifulSoup(html_content, "html.parser")
    main_element = soup.find("main") or soup.find("article")
    return str(main_element) if main_element else html_content


def extract_info_with_mistral(url, html_content):
    """Send the HTML to Mistral AI and get structured data."""
    prompt = f"""
    Extract structured data from the following newspaper article HTML.

    ### **Instructions**:
    - Extract **title** from the article.
    - Extract **content** (full text of the article) by getting all text inside `<p>` tags`, preserving order.
    - **Do NOT summarize, remove, or modify sentences**.
    - Extract **images** and their **captions**.
    - If a caption is missing, return an empty string `""`.
    - The output **must** be a valid JSON object following this structure.

    ---

    ### **Example Output (Mimic this format)**
    ```json
    {{
      "url": "https://example.com/article-123",
      "title": "Breaking News: AI Revolutionizes Data Extraction",
      "content": "Artificial Intelligence (AI) is transforming data processing...",
      "metadata": [
        {{
          "image_url": "https://example.com/image1.jpg",
          "description": "A group of researchers working on AI models."
        }},
        {{
          "image_url": "https://example.com/image2.jpg",
          "description": ""
        }}
      ]
    }}
    ```

    ---

    ### **Now extract structured data from the given article:**
    **URL**: {url}  

    **HTML Content**: {html_content}
        """

    response = structured_llm.invoke([HumanMessage(content=prompt)])
    response_dict = response.model_dump()  # Convert to dictionary

    # Fix schema mismatches
    # response_dict["content"] = response_dict.pop("full_text_content", "")
    # response_dict["metadata"] = [
    #     {"image_url": img["url"], "description": img.get("caption", "")}
    #     for img in response_dict.pop("images", [])
    # ]
    response_dict.setdefault("url", url)  # Ensure URL exists

    return Article(**response_dict)  # Validate with Pydantic


def scrape_and_extract(url):
    """Fetch HTML, extract content, and parse structured data."""
    html_content = fetch_html(url)
    main_html = extract_main_content(html_content)
    obj = extract_info_with_mistral(url, main_html)
    figures = []
    for figure in obj.metadata:
        figures.append([figure.image_url, figure.description])
    obj_dict = extract_info_with_mistral(url, main_html).model_dump()
    obj_dict['metadata'] = figures

    return obj_dict


async def main2():
    url = "https://dantri.com.vn/giao-duc/truong-quoc-te-bat-ngo-gui-thu-de-nghi-phu-huynh-phai-chuyen-truong-20250215154617281.htm"
    start = time.time()
    result = scrape_and_extract(url)
    end = time.time()

    print(json.dumps(result, indent=2, ensure_ascii=False))  # ✅ Vietnamese characters
    print("It took", end - start, "seconds!")

asyncio.run(main2())
