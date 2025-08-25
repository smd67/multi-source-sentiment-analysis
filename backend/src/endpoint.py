"""
Playwright driver that executes operations based on a profile.
"""

import argparse
import requests
import Levenshtein
import openai
import os
from enum import Enum

import bonobo
import googleapiclient.discovery
from bonobo.config import use
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, List, Dict, Generator, Tuple
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from polygon import RESTClient
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from nltk.sentiment import SentimentIntensityAnalyzer
from download import download  # pylint: disable=import-error

origins = ["*"]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChainType(Enum):
    """
    Enumeration of graph chain types.
    """
    LOGO_DATA = 1
    DESCRPTION_DATA = 2
    STOCK_INFO_DATA = 3
    STOCK_PRICE_DATA = 4

class Logo(BaseModel):
    index: int
    url: str
    title: str
    distance: int

class TargetQuery(BaseModel):
    target: str

class Description(BaseModel):
    text: str

class StockInfo(BaseModel):
    ticker_symbol: str
    company_name: str
    stock_price: float

class StockData(BaseModel):
    month: str
    price: float

class CombinedData(BaseModel):
    logo: List[Logo]
    description: Description
    stock_info: StockInfo
    stock_data: List[StockData]

# Global data
KV_STORE: Dict[ChainType, Any] = (
    {}
)  # Key-Value storage for the transform results


@app.post("/get-logo/")
def get_logo(query: TargetQuery) -> List[Logo]:
    url = "https://www.brandsoftheworld.com"

    results = []
    target = query.target
    # Open playwright and goto url
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        # You can use various locators like get_by_label, get_by_placeholder, or css selectors
        page.locator("#edit-search-api-views-fulltext").fill(target)
        submit_button = page.locator('input[type="submit"][value="Search"]')
        submit_button.click()
        html_content = page.content()
        browser.close()

        soup = BeautifulSoup(html_content, 'html.parser')
        elements_with_class = soup.find('div', class_="view-content")
        list_items = elements_with_class.find_all('li')
        for index, element in enumerate(list_items):
            result_element = {}
            result_element['index'] = index
            for a in element.find_all('img'):
                full_url = a['src']
                url = full_url.split('?')[0]
                result_element['url'] = url
            for a in element.find_all('span'):
                result_element['title'] = a.text
                result_element['distance'] = Levenshtein.distance(target, a.text)
            results.append(result_element)
        
        sorted_by_index = sorted(results, key=lambda x: x['index'])
        sorted_by_distance = sorted(sorted_by_index, key=lambda x: x['distance'])
   
    return [Logo(**logo_dict) for logo_dict in sorted_by_distance]
        
@app.post("/get-description/")
def get_description(query: TargetQuery) -> Description:
    target = query.target
    api_key = os.environ.get("OPENAI_API_KEY")

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Briefly describe the company {target} in a pargraph"},
        ]
    )
    return Description(text=response.choices[0].message.content)

@app.post("/get-stock-info/")
def get_stock_info(query: TargetQuery) -> StockInfo:
    target = query.target
    base_url = f"https://stockanalysis.com/symbol-lookup"
    # Define the query parameters with a space
    params = {
        "q": target,
    }

    header_mapping = {
        0: "ticker_symbol",
        1: "company_name",
        2: None,
        3: "stock_price",
        4: None
    }
    
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    
    result = {}
    html_content = response.text
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', class_="svelte-1swpzu1")
    for row in table.find_all('tr'):
        result = {}
        cells = row.find_all(['td'])
        for index, cell in enumerate(cells):
            if header_mapping[index]:
                result[header_mapping[index]] = cell.get_text()
        if 'ticker_symbol' in result:
            break
    res = StockInfo(**result)
    return res

@app.post("/get-stock-data/")
def get_stock_data(query: TargetQuery) -> List[StockData]:
    months = [
        None,
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec"
    ]
    target = query.target
    api_key = os.environ.get("POLYGON_API_KEY")
    client = RESTClient(api_key=api_key)
    res = client.list_tickers(search=target, market="stocks", limit=1)
    item = next(res)
    ticker = item.ticker
    # Get the current date
    current_date = date.today()
    twelve_months_prior = current_date - relativedelta(months=12)

    stock_data = []
    for a in client.list_aggs(ticker=ticker, 
                              multiplier=1, 
                              timespan="month", 
                              from_=f"{twelve_months_prior.strftime('%Y-%m-%d')}", 
                              to=f"{current_date.strftime('%Y-%m-%d')}", 
                              limit=50000):
        price = a.close
        ts = a.timestamp // 1000
        month = datetime.fromtimestamp(ts).month
        stock_data.append({"month": months[month], "price": price})
    print(stock_data)
    return [StockData(**stock_dict) for stock_dict in stock_data]

@use("query")
def extract_logo_data(query: TargetQuery) -> Generator[Tuple[ChainType, List[Logo]], None, None]:
    data = get_logo(query)
    yield (ChainType.LOGO_DATA, data)

@use("query")
def extract_description(query: TargetQuery) -> Generator[Tuple[ChainType, Description], None, None]:
    data = get_description(query)
    yield (ChainType.DESCRPTION_DATA, data)

@use("query")
def extract_stock_info(query: TargetQuery) -> Generator[Tuple[ChainType, StockInfo], None, None]:
    data = get_stock_info(query)
    yield (ChainType.STOCK_INFO_DATA, data)

@use("query")
def extract_stock_data(query: TargetQuery) -> Generator[Tuple[ChainType, StockInfo], None, None]:
    data = get_stock_data(query)
    yield (ChainType.STOCK_PRICE_DATA, data)

def store_results(key: ChainType, data: BaseModel):
    """
    Store transform results for final processing.

    Parameters
    ----------
    key : str
        The type of data (channel_data or comment_thread_data)
    df : pd.DataFrame
        The dataframe output by the transform function.
    """
    print("IN store_results")
    KV_STORE[key] = data

def get_services(query: TargetQuery) -> Dict[str, Any]:
    """
    Method used to pass global data and services into graph.

    Parameters
    ----------
    query : str
        The query string that is mapped to a q value in the youtube api call.

    Returns
    -------
    dict[str, Any]
        Returns a dictionary of services for a graph.
    """
    return {"query": query}

@app.post("/get-all-data/")
def get_all_data(query: TargetQuery):
    # Create the Bonobo graph
    graph = bonobo.Graph()
    graph.add_chain(store_results, _input=None)
    graph.add_chain(
        extract_logo_data,
        store_results,
    )
    graph.add_chain(
        extract_description,
        store_results,
    )
    graph.add_chain(
        extract_stock_info,
        store_results,
    )
    graph.add_chain(
        extract_stock_data,
        store_results,
    )
    graph.add_chain(
        extract_search_data,
        extract_comment_thread_data,
        transform_comment_thread_data,
        store_results,
    )
    bonobo.run(graph, services=get_services(query))
    logo = KV_STORE[ChainType.LOGO_DATA]
    description = KV_STORE[ChainType.DESCRPTION_DATA]
    stock_info = KV_STORE[ChainType.STOCK_INFO_DATA]
    stock_data = KV_STORE[ChainType.STOCK_PRICE_DATA]
    return CombinedData(logo=logo, description=description, stock_info=stock_info, stock_data=stock_data)

def perform_sentiment_analysis(text: str) -> float:
    """
    Perform a sentiment analysis on each comment.

    Parameters
    ----------
    text : str
       The string to be analyzed.

    Returns
    -------
    float
        A value between 0.0 and 1.0 with 0.0 being no positive sentiment and
        1.0 being 100% positive sentiment.
    """
    # Initialize VADER sentiment analyzer
    sid = SentimentIntensityAnalyzer()

    # Perform sentiment analysis
    sentiment_score = sid.polarity_scores(text)["pos"]
    return sentiment_score

@use("query")
def extract_search_data(
    query: str,
) -> Generator[List[Tuple[str, str]], None, None]:
    """
    Search for videos that match a query string.

    Parameters
    ----------
    query : str
        The query string used in the "q" parameter.

    Yields
    ------
    Generator[list[tuple[str, str]], None, None]
        A list of tuple pairs (video_id, channel_id)
    """
    MAX_RESULTS_PER_PAGE = 50
    MAX_PAGES = 5

    api_service_name = "youtube"
    api_version = "v3"
    api_key = os.environ.get("DEVELOPER_KEY")
    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, developerKey=api_key
    )

    response_list: List[Any] = []
    params = {
        "part": "snippet",
        "q": query.target,
        "maxResults": MAX_RESULTS_PER_PAGE,
        "safeSearch": "none",
    }
    while True:
        page_token = None

        if len(response_list) >= MAX_PAGES:
            break

        try:
            request = youtube.search().list(**params)  # type: ignore
            response = request.execute()
            response_list.append(response)
            page_token = response.get("nextPageToken")
        except googleapiclient.errors.HttpError as e:
            print(f"Error: unexpected exception e={e}")

        if page_token:
            params = {"part": "snippet", "q": query, "pageToken": page_token}
        else:
            break
    search_data = []
    for response in response_list:
        for item in response.get("items", []):
            video_id = item.get("id", {}).get("videoId")
            channel_id = item.get("snippet", {}).get("channelId")
            search_data.append((video_id, channel_id))
    yield search_data

def extract_comment_thread_data(
    search_data: List[Tuple[str, str]]
) -> Generator[Dict[str, List[Any]], None, None]:
    """
    Extract comments for all of the videos.

    Parameters
    ----------
    search_data : list[tuple[str, str]]
        A list of tuple pairs (video_id, channel_id)

    Yields
    ------
    Generator[dict[str, list[Any]], None, None]
        Returs a dictionary with an "items" key whose value is the JSON data
        of all of the responses.
    """
    api_service_name = "youtube"
    api_version = "v3"
    api_key = os.environ.get("DEVELOPER_KEY")
    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, developerKey=api_key
    )

    data: Dict[str, List[Any]] = {}
    data["items"] = []
    videos: Dict[str, List[Any]] = {}
    n = 2

    # Create dictionary
    for list_item in search_data:
        video_id = list_item[0]
        channel_id = list_item[1]
        if channel_id not in videos:
            videos[channel_id] = []
        videos[channel_id].append(video_id)

    for channel_id, video_list in videos.items():
        if len(video_list) > 2:
            video_list = random.sample(video_list, n)
        for video_id in video_list:
            try:
                request = youtube.commentThreads().list(  # type: ignore
                    part="id, replies, snippet", videoId=video_id
                )
                response = request.execute()
                data["items"].append(response)
            except googleapiclient.errors.HttpError:
                pass
    yield data

def transform_comment_thread_data(
    comment_thread_data: Dict,
) -> Generator[Tuple[ChainType, pd.DataFrame], None, None]:
    """
    Transform the comment_thread_data into a useable dataframe.
    Parameters

    Parameters
    ----------
    comment_thread_data : dict
        A dictionary containing the comment thread data.

    Yields
    ------
    Generator[tuple[ChainType, pd.DataFrame], None, None]
        A tuple pair (key, df) that contains the type of data and a
        useable dataframe.
    """

    print("in transform_comment_thread_data")
    data = []
    for item in comment_thread_data.get("items", []):
        for comment_item in item.get("items", []):
            channel_id = comment_item.get("snippet", {}).get("channelId", "")
            top_level = (
                comment_item.get("snippet", {})
                .get("topLevelComment", {})
                .get("snippet", {})
            )
            comment_text = top_level.get("textOriginal", "")
            score = perform_sentiment_analysis(comment_text)
            data.append((channel_id, score))
            for reply in comment_item.get("replies", {}).get("comments", []):
                comment_text = reply.get("snippet", {}).get("textOriginal", "")
                score = perform_sentiment_analysis(comment_text)
                data.append((channel_id, score))
    df = pd.DataFrame(data, columns=["Channel_Id", "Score"])
    grouped_data = df.groupby("Channel_Id")["Score"].mean()
    result_df = grouped_data.reset_index()
    yield (ChainType.COMMENT_THREAD_DATA, result_df)

if __name__ == "__main__":

    # 1. Create an ArgumentParser object
    parser = argparse.ArgumentParser(
        description="A simple logo lookup for a company by descriptive string"
    )

    # 2. Add arguments
    parser.add_argument("--target", type=str, help="Descriptive text for the company. ie; Pepsi")

    # 3. Parse the arguments
    args = parser.parse_args()

    query = TargetQuery(target=args.target)
    val = get_stock_data(query)