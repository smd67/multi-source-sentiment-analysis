from enum import Enum
from pydantic import BaseModel
from typing import List


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


class Sentiment(BaseModel):
    score: float


class CombinedData(BaseModel):
    logo: List[Logo]
    description: Description
    stock_info: StockInfo
    stock_data: List[StockData]
    youtube_sentiment: Sentiment
    reddit_sentiment: Sentiment
