"""
This module implements the youtube sentiment analysis functions.
"""

import random
from typing import Any, Dict, Generator, List, Tuple

import googleapiclient.discovery
from common import (  # pylint: disable=import-error
    SERVICES,
    get_secret,
    perform_sentiment_analysis,
)
from decorators import span_decorator  # pylint: disable=import-error
from model import ChainType, Sentiment  # pylint: disable=import-error


def extract_search_data() -> Generator[List[Tuple[str, str]], None, None]:
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
    search_data = perform_extract_search_data()
    yield search_data


@span_decorator
def perform_extract_search_data() -> List[Any]:
    MAX_RESULTS_PER_PAGE = 50
    MAX_PAGES = 5
    query = SERVICES["query"]

    api_service_name = "youtube"
    api_version = "v3"
    api_key = get_secret("GOOGLE_API_KEY")
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
    return search_data


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
    data: Dict[str, List[Any]] = perform_extract_comment_thread_data(search_data)
    yield data


@span_decorator
def perform_extract_comment_thread_data(search_data: List[Tuple[str, str]]):
    api_service_name = "youtube"
    api_version = "v3"
    api_key = get_secret("GOOGLE_API_KEY")
    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, developerKey=api_key
    )

    data: Dict[str, List[Any]] = {}
    data["items"] = []
    videos: List[Any] = []
    n = 100

    # Create dictionary
    for list_item in search_data:
        video_id = list_item[0]
        videos.append(video_id)

    if len(videos) > n:
        videos = random.sample(videos, n)
    for video_id in videos:
        try:
            request = youtube.commentThreads().list(  # type: ignore
                part="id, replies, snippet", videoId=video_id
            )
            response = request.execute()
            data["items"].append(response)
        except googleapiclient.errors.HttpError:
            pass
    return data


def transform_comment_thread_data(
    comment_thread_data: Dict,
) -> Generator[Tuple[ChainType, Sentiment], None, None]:
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
    percentage = perform_transform_comment_thread_data(comment_thread_data)
    yield (ChainType.YOUTUBE_SENTIMENT_DATA, Sentiment(score=percentage))


@span_decorator
def perform_transform_comment_thread_data(comment_thread_data: Dict) -> float:
    POSITIVE_THRESHOLD = 0.1
    NEGATIVE_THRESHOLD = -0.1
    data = []
    for item in comment_thread_data.get("items", []):
        for comment_item in item.get("items", []):
            top_level = (
                comment_item.get("snippet", {})
                .get("topLevelComment", {})
                .get("snippet", {})
            )
            comment_text = top_level.get("textOriginal", "")
            score = perform_sentiment_analysis(comment_text)
            data.append(score)
            for reply in comment_item.get("replies", {}).get("comments", []):
                comment_text = reply.get("snippet", {}).get("textOriginal", "")
                score = perform_sentiment_analysis(comment_text)
                data.append(score)
    boolean_array = [
        True if val >= POSITIVE_THRESHOLD else False
        for val in data
        if val >= POSITIVE_THRESHOLD or val <= NEGATIVE_THRESHOLD
    ]
    true_count = sum(boolean_array)
    total_elements = len(boolean_array)
    percentage = (
        (true_count / total_elements) * 100.0 if total_elements > 0 else 0.0
    )
    return percentage
