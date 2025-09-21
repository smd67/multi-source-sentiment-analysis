"""
Playwright driver that executes operations based on a profile.
"""

import argparse
from datetime import date, datetime
from typing import Any, Dict, Generator, List, Tuple

import bonobo
import Levenshtein
import openai
import requests
from bs4 import BeautifulSoup
from common import SERVICES, get_secret  # pylint: disable=import-error
from dateutil.relativedelta import relativedelta
from decorators import span_decorator  # pylint: disable=import-error
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from model import (  # pylint: disable=import-error
    ChainType,
    CombinedData,
    Description,
    Logo,
    Sentiment,
    StockData,
    StockInfo,
    TargetQuery,
)
from opentelemetry import trace  # pylint: disable=import-error
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
KV_STORE: Dict[ChainType, Any] = {}  # Key-Value storage for the transform results


@app.post("/get-logo/")
@span_decorator
def get_logo(query: TargetQuery) -> List[Logo]:
    """
    API call to get a company's logo based on it's common name.

    Parameters
    ----------
    query : TargetQuery
        The common name of the company.

    Returns
    -------
    List[Logo]
        A list of urls ranked by Levenshtein distance. This ensures we get a logo
        that is close to what we queried and not just the most popular one.
    """
    url = "https://www.brandsoftheworld.com"

    results = []
    target = query.target
    current_span = trace.get_current_span()
    current_span.set_attribute("target_query", target)
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
                result_element["distance"] = Levenshtein.distance(target, a.text)
            results.append(result_element)

        sorted_by_index = sorted(results, key=lambda x: x["index"])
        sorted_by_distance = sorted(sorted_by_index, key=lambda x: x["distance"])

    return [Logo(**logo_dict) for logo_dict in sorted_by_distance]


@app.post("/get-description/")
@span_decorator
def get_description(query: TargetQuery) -> Description:
    """
    Use chat gpt to write a simple description of the target company.

    Parameters
    ----------
    query : TargetQuery
        The common name of the company.

    Returns
    -------
    Description
        A simple description of the company.
    """
    target = query.target
    current_span = trace.get_current_span()
    current_span.set_attribute("target_query", target)
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
@span_decorator
def get_stock_info(query: TargetQuery) -> StockInfo:
    """
    Get stock info such as ticker name and closing price.

    Parameters
    ----------
    query : TargetQuery
        The common name of the company.

    Returns
    -------
    StockInfo
        An object containing the ticker symbol, company name, and closing price.
    """
    target = query.target
    current_span = trace.get_current_span()
    current_span.set_attribute("target_query", target)
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
@span_decorator
def get_stock_data(query: TargetQuery) -> List[StockData]:
    """
    Get historical stock price data from polygon.

    Parameters
    ----------
    query : TargetQuery
        The common name of the company.

    Returns
    -------
    List[StockData]
        A list of ("month", "stock price") objects for the last 12 months.
    """
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
    current_span = trace.get_current_span()
    current_span.set_attribute("target_query", target)

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
@span_decorator
def get_all_data(query: TargetQuery) -> CombinedData:
    """
    This is a method that collects all data in a single call using a
    multi-threaded pipeline.

    Parameters
    ----------
    query : TargetQuery
        The common name of the company.

    Returns
    -------
    CombinedData
        All of the collected data in a single object.

    Raises
    ------
    Exception
        Will raise an exception if a pipeline error occurs.
    """
    current_span = trace.get_current_span()
    current_span.set_attribute("target_query", query.target)

    print(f"IN get_all_data. query={query.target}")
    # Create the Bonobo graph
    SERVICES["query"] = query
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
    result = bonobo.run(graph)

    # Check for pipeline errors and raise an exception.
    error_list = []
    for node in result:
        stat_string = node.get_statistics_as_string(prefix=" ")
        print(f"stat_string={stat_string}")
        stat_array = stat_string.split(" ")
        if any([True if "err=" in stat else False for stat in stat_array]):
            print(f"Errors: {str(node)}")
            error_list.append(str(node))
    if len(error_list) > 0:
        raise Exception(
            f"Errors occurred during pipeline execution: {','.join(error_list)}"
        )

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
@span_decorator
def get_youtube_sentiment(query: TargetQuery) -> Sentiment:
    """
    Get the youtube sentiment for a company run as a pipeline.

    Parameters
    ----------
    query : TargetQuery
        The common name of the company.

    Returns
    -------
    Sentiment
        The results of the sentiment analysis
    """
    current_span = trace.get_current_span()
    current_span.set_attribute("target_query", query.target)

    # Create the Bonobo graph
    SERVICES["query"] = query
    graph = bonobo.Graph()
    graph.add_chain(store_results, _input=None)
    graph.add_chain(
        extract_search_data,
        extract_comment_thread_data,
        transform_comment_thread_data,
        store_results,
    )
    bonobo.run(graph)
    return KV_STORE[ChainType.YOUTUBE_SENTIMENT_DATA]


@app.post("/get-reddit-sentiment/")
@span_decorator
def get_reddit_sentiment(query: TargetQuery) -> Sentiment:
    """
    Get the reddit sentiment for a company run as a pipeline.

    Parameters
    ----------
    query : TargetQuery
        The common name of the company.

    Returns
    -------
    Sentiment
        The results of the sentiment analysis
    """
    current_span = trace.get_current_span()
    current_span.set_attribute("target_query", query.target)

    # Create the Bonobo graph
    SERVICES["query"] = query
    graph = bonobo.Graph()
    graph.add_chain(store_results, _input=None)
    graph.add_chain(
        reddit_extract_search_data,
        reddit_extract_comment_thread_data,
        reddit_transform_comment_thread_data,
        store_results,
    )
    bonobo.run(graph)
    return KV_STORE[ChainType.REDDIT_SENTIMENT_DATA]


def extract_logo_data() -> Generator[Tuple[ChainType, List[Logo]], None, None]:
    """
    Wrapper function to get the logo suitable for a pipeline.

    Yields
    ------
    Generator[Tuple[ChainType, List[Logo]], None, None]
        A generator for pipeline usage.
    """
    query = SERVICES["query"]
    data = get_logo(query)
    yield (ChainType.LOGO_DATA, data)


def extract_description() -> Generator[Tuple[ChainType, Description], None, None]:
    """
    Wrapper function to get a company description suitable for a pipeline.

    Yields
    ------
    Generator[Tuple[ChainType, Description], None, None]
        A generator containing the type and object
    """
    query = SERVICES["query"]
    data = get_description(query)
    yield (ChainType.DESCRPTION_DATA, data)


def extract_stock_info() -> Generator[Tuple[ChainType, StockInfo], None, None]:
    """
    Wrapper function to get a company stock information suitable for a pipeline.

    Yields
    ------
    Generator[Tuple[ChainType, StockInfo], None, None]
         A generator containing the type and object
    """
    query = SERVICES["query"]
    data = get_stock_info(query)
    yield (ChainType.STOCK_INFO_DATA, data)


def extract_stock_data() -> Generator[Tuple[ChainType, StockInfo], None, None]:
    """
    Wrapper function to get a company's historical stock data suitable for
    a pipeline.

    Yields
    ------
    Generator[Tuple[ChainType, StockInfo], None, None]
        A generator containing the type and object
    """
    query = SERVICES["query"]
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
    KV_STORE[key] = data


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
    val = get_all_data(query)
    print(val)
