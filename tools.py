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
    # return result

    out = []

    for r in res['results']:
        out.append(f"Title:{r['title']} \n URL: {r['url']} \n Content: {r['content'][:300]}\n")

    final_output = "\n---\n".join(out)
    return final_output



#max_results - specifies the maximum number of web search results Tavily should return for a query.
#slicing of string : str[:x] - start index is omitted so python starts at index 0 and end index is x which is exclusive so returns characters at indices 0 through x-1.
# print(web_search.invoke("what is the news on french revolts in this year 2026?"))

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

# print(web_scrape.invoke("https://en.wikipedia.org/wiki/Quentin_Tarantino"))


