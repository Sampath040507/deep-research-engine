from langchain.tools import tool
from tavily import TavilyClient
from dotenv import load_dotenv
load_dotenv()  
import os 
from rich import print

from bs4 import BeautifulSoup
import requests

tavily_client = TavilyClient(os.getenv("TAVILY_API_KEY"))

@tool
def web_search(q: str)-> str:
    """Search the web for recent and reliable information on a topic . Returns Titles , URLs and snippets of the top results."""
    res = tavily_client.search(query= q, max_results=2)
   
    out = []

    for r in res['results']:
        out.append(f"Title:{r['title']} \n URL: {r['url']} \n Content: {r['content'][:300]}\n")

    final_output = "\n---\n".join(out)
    return final_output


@tool
def web_scrape(url: str) -> str:
    """Scrape and return clean text content from a given URL for deeper reading."""
    try:
        resp = requests.get(url, timeout=8, headers={'User-Agent':'Mozilla/5.0'})
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(['style', 'nav', 'footer', 'script']):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:3000]
    except Exception as e:
        return f"could not scrape url: {str(e)}"
