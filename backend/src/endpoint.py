"""
Playwright driver that executes operations based on a profile.
"""

import argparse
import os
from datetime import date, datetime
from typing import Any, Dict, Generator, List, Tuple

import bonobo
import Levenshtein
import openai
import requests
from bonobo.config import use
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from model import (  # pylint: disable=import-error
    ChainType,
    CombinedData,
    Description,
    Logo,
    StockData,
    StockInfo,
    TargetQuery,
    Sentiment
)
from playwright.sync_api import sync_playwright
from polygon import RESTClient
from pydantic import BaseModel
from reddit import (  # pylint: disable=import-error
    reddit_extract_comment_thread_data,
    reddit_extract_search_data,
    reddit_transform_comment_thread_data,
)
from youtube import (  # pylint: disable=import-error
    extract_comment_thread_data,
    extract_search_data,
    transform_comment_thread_data,
)
from common import get_secret

origins = ["*"]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        # You can use various locators like get_by_label, get_by_placeholder,
        # or css selectors
        page.locator("#edit-search-api-views-fulltext").fill(target)
        submit_button = page.locator('input[type="submit"][value="Search"]')
        submit_button.click()
        html_content = page.content()
        browser.close()

        soup = BeautifulSoup(html_content, "html.parser")
        elements_with_class = soup.find("div", class_="view-content")
        list_items = elements_with_class.find_all("li")
        for index, element in enumerate(list_items):
            result_element: Dict[str, Any] = {}
            result_element["index"] = index
            for a in element.find_all("img"):
                full_url = a["src"]
                url = full_url.split("?")[0]
                result_element["url"] = url
            for a in element.find_all("span"):
                result_element["title"] = a.text
                result_element["distance"] = Levenshtein.distance(
                    target, a.text
                )
            results.append(result_element)

        sorted_by_index = sorted(results, key=lambda x: x["index"])
        sorted_by_distance = sorted(
            sorted_by_index, key=lambda x: x["distance"]
        )

    return [Logo(**logo_dict) for logo_dict in sorted_by_distance]


@app.post("/get-description/")
def get_description(query: TargetQuery) -> Description:
    target = query.target
    api_key = get_secret("OPENAI_API_KEY")

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": f"Briefly describe the company {target} "
                + "in a pargraph",
            },
        ],
    )
    return Description(text=response.choices[0].message.content)


@app.post("/get-stock-info/")
def get_stock_info(query: TargetQuery) -> StockInfo:
    target = query.target
    base_url = "https://stockanalysis.com/symbol-lookup"

    # Define the query parameters with a space
    params = {
        "q": target,
    }

    header_mapping = {
        0: "ticker_symbol",
        1: "company_name",
        2: None,
        3: "stock_price",
        4: None,
    }

    response = requests.get(base_url, params=params)
    response.raise_for_status()

    result: Dict[Any, Any] = {}
    html_content = response.text
    soup = BeautifulSoup(html_content, "html.parser")
    table = soup.find("table", class_="svelte-1swpzu1")
    for row in table.find_all("tr"):
        result = {}
        cells = row.find_all(["td"])
        for index, cell in enumerate(cells):
            if header_mapping[index]:
                result[header_mapping[index]] = cell.get_text()
        if "ticker_symbol" in result:
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
        "Dec",
    ]
    target = query.target
    api_key = get_secret("POLYGON_API_KEY")
    client = RESTClient(api_key=api_key)
    res = client.list_tickers(search=target, market="stocks", limit=1)
    item = next(res)
    ticker = item.ticker
    # Get the current date
    current_date = date.today()
    twelve_months_prior = current_date - relativedelta(months=12)

    stock_data = []
    for a in client.list_aggs(
        ticker=ticker,
        multiplier=1,
        timespan="month",
        from_=f"{twelve_months_prior.strftime('%Y-%m-%d')}",
        to=f"{current_date.strftime('%Y-%m-%d')}",
        limit=50000,
    ):
        price = a.close
        ts = a.timestamp // 1000
        month = datetime.fromtimestamp(ts).month
        stock_data.append({"month": months[month], "price": price})
    return [StockData(**stock_dict) for stock_dict in stock_data]


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
    graph.add_chain(
        reddit_extract_search_data,
        reddit_extract_comment_thread_data,
        reddit_transform_comment_thread_data,
        store_results,
    )
    bonobo.run(graph, services=get_services(query))
    logo = KV_STORE[ChainType.LOGO_DATA]
    description = KV_STORE[ChainType.DESCRPTION_DATA]
    stock_info = KV_STORE[ChainType.STOCK_INFO_DATA]
    stock_data = KV_STORE[ChainType.STOCK_PRICE_DATA]
    youtube_sentiment = KV_STORE[ChainType.YOUTUBE_SENTIMENT_DATA]
    reddit_sentiment = KV_STORE[ChainType.REDDIT_SENTIMENT_DATA]
    return CombinedData(
        logo=logo,
        description=description,
        stock_info=stock_info,
        stock_data=stock_data,
        youtube_sentiment=youtube_sentiment,
        reddit_sentiment=reddit_sentiment,
    )


@app.post("/get-youtube-sentiment/")
def get_youtube_sentiment(query: TargetQuery):
    # Create the Bonobo graph
    graph = bonobo.Graph()
    graph.add_chain(store_results, _input=None)
    graph.add_chain(
        extract_search_data,
        extract_comment_thread_data,
        transform_comment_thread_data,
        store_results,
    )
    bonobo.run(graph, services=get_services(query))
    return KV_STORE[ChainType.YOUTUBE_SENTIMENT_DATA]


@app.post("/get-reddit-sentiment/")
def get_reddit_sentiment(query: TargetQuery):
    # Create the Bonobo graph
    graph = bonobo.Graph()
    graph.add_chain(store_results, _input=None)
    graph.add_chain(
        reddit_extract_search_data,
        reddit_extract_comment_thread_data,
        reddit_transform_comment_thread_data,
        store_results,
    )
    bonobo.run(graph, services=get_services(query))
    return KV_STORE[ChainType.REDDIT_SENTIMENT_DATA]


@use("query")
def extract_logo_data(
    query: TargetQuery,
) -> Generator[Tuple[ChainType, List[Logo]], None, None]:
    data = get_logo(query)
    yield (ChainType.LOGO_DATA, data)


@use("query")
def extract_description(
    query: TargetQuery,
) -> Generator[Tuple[ChainType, Description], None, None]:
    data = get_description(query)
    yield (ChainType.DESCRPTION_DATA, data)


@use("query")
def extract_stock_info(
    query: TargetQuery,
) -> Generator[Tuple[ChainType, StockInfo], None, None]:
    data = get_stock_info(query)
    yield (ChainType.STOCK_INFO_DATA, data)


@use("query")
def extract_stock_data(
    query: TargetQuery,
) -> Generator[Tuple[ChainType, StockInfo], None, None]:
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


if __name__ == "__main__":

    # 1. Create an ArgumentParser object
    parser = argparse.ArgumentParser(
        description="A simple logo lookup for a company by descriptive string"
    )

    # 2. Add arguments
    parser.add_argument(
        "--target", type=str, help="Descriptive text for the company. ie; Pepsi"
    )

    # 3. Parse the arguments
    args = parser.parse_args()

    query = TargetQuery(target=args.target)
    val = get_reddit_sentiment(query)
    print(val)
