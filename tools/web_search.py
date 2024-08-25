# web_search.py
import requests


def search_web(query):
    """
    Perform a web search using the DuckDuckGo Instant Answer API.
    """
    url = f"https://api.duckduckgo.com/?q={query}&format=json"
    response = requests.get(url)
    data = response.json()

    if data['Abstract']:
        return data['Abstract']
    elif data['RelatedTopics']:
        return data['RelatedTopics'][0]['Text']
    else:
        return "No results found."


tool = {
    "name": "web_search",
    "description": "Search the web for information on a given query",
    "function": search_web
}