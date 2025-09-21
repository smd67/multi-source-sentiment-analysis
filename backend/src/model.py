"""
Pydantic model for the Stock Analyzer API
"""

from enum import Enum
from typing import List

from pydantic import BaseModel


class ChainType(Enum):
    """
    Enumeration of graph chain types.
    """

    LOGO_DATA = 1
    DESCRPTION_DATA = 2
    STOCK_INFO_DATA = 3
    STOCK_PRICE_DATA = 4
    YOUTUBE_SENTIMENT_DATA = 5
    REDDIT_SENTIMENT_DATA = 6


class Logo(BaseModel):
    """
    Model for Logo data
    """

    index: int
    url: str
    title: str
    distance: int


class TargetQuery(BaseModel):
    """
    Model for query
    """

    target: str


class Description(BaseModel):
    """
    Model for company description
    """

    text: str


class StockInfo(BaseModel):
    """
    Model for stock info
    """

    ticker_symbol: str
    company_name: str
    stock_price: float


class StockData(BaseModel):
    """
    Model for stock data
    """

    month: str
    price: float


class Sentiment(BaseModel):
    """
    Model for sentiment analysis score
    """

    score: float


class CombinedData(BaseModel):
    """
    Model for combined data to return all collected data in
    one API call.
    """

    logo: List[Logo]
    description: Description
    stock_info: StockInfo
    stock_data: List[StockData]
    youtube_sentiment: Sentiment
    reddit_sentiment: Sentiment
