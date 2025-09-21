"""
This module implements reddit sentiment analysis functions.
"""

import random
from typing import Any, Generator, List, Tuple  # pylint: disable=import-error

import praw
from common import (  # pylint: disable=import-error
    SERVICES,
    get_secret,
    perform_sentiment_analysis,
)
from decorators import span_decorator  # pylint: disable=import-error
from model import TargetQuery  # pylint: disable=import-error
from model import ChainType, Sentiment  # pylint: disable=import-error
from praw.models import MoreComments


def reddit_extract_search_data() -> Generator[List[str], None, None]:
    """
    Method to extract sewarch data suitable for pipeline usage.

    Yields
    ------
    Generator[List[str], None, None]
        A Generator containing the list of search data
    """
    search_data = []
    query = SERVICES["query"]
    search_data = perform_reddit_extract_search_data(query)
    yield search_data


@span_decorator
def perform_reddit_extract_search_data(query: TargetQuery) -> List[Any]:
    """
    Method that performs the actual search.

    Parameters
    ----------
    query : TargetQuery
        The common name of the company

    Returns
    -------
    List[Any]
        A list of search data results
    """
    MAX_RESULTS = 100
    client_id = get_secret("REDDIT_CLIENT_ID")
    client_secret = get_secret("REDDIT_CLIENT_SECRET")
    user_agent = "sdimig-user-agent"
    search_data = []
    reddit = praw.Reddit(
        client_id=client_id, client_secret=client_secret, user_agent=user_agent
    )
    subreddit = reddit.subreddit("AskReddit")
    for submission in subreddit.search(query.target, limit=MAX_RESULTS):
        search_data.append(submission)
    return search_data


def reddit_extract_comment_thread_data(
    search_data: List[str],
) -> Generator[List[str], None, None]:
    """
    Method to extract comment thread data suitable for pipeline execution

    Parameters
    ----------
    search_data : List[str]
       The search data results

    Yields
    ------
    Generator[List[str], None, None]
        A generator including the list suitable as input to another
        pipeline node.
    """
    yield perform_reddit_extract_comment_thread_data(search_data)


@span_decorator
def perform_reddit_extract_comment_thread_data(
    search_data: List[str],
) -> List[Any]:
    """
    Method that does the actual work of extracting pipeline data.

    Parameters
    ----------
    search_data : List[str]
        A list of search data results.

    Returns
    -------
    List[Any]
        A list of comment thread data
    """
    client_id = get_secret("REDDIT_CLIENT_ID")
    client_secret = get_secret("REDDIT_CLIENT_SECRET")
    user_agent = "sdimig-user-agent"
    reddit = praw.Reddit(
        client_id=client_id, client_secret=client_secret, user_agent=user_agent
    )
    n = 25
    comment_thread_data = []

    ids = search_data
    if len(ids) > n:
        ids = random.sample(search_data, n)
    for id in ids:
        submission = reddit.submission(id)
        for top_level_comment in submission.comments:
            if isinstance(top_level_comment, MoreComments):
                continue
            comment_thread_data.append(top_level_comment.body)
    return comment_thread_data


def reddit_transform_comment_thread_data(
    comment_thread_data: List[str],
) -> Generator[Tuple[ChainType, Sentiment], None, None]:
    """
    A method that transforms comment thread data into a sentiment
    score suitable for pipeline execution.

    Parameters
    ----------
    comment_thread_data : List[str]
        A list of comment thread data

    Yields
    ------
    Generator[Tuple[ChainType, Sentiment], None, None]
        A generator containing the type and sentiment object.
    """
    percentage = perform_reddit_transform_comment_thread_data(comment_thread_data)
    yield (ChainType.REDDIT_SENTIMENT_DATA, Sentiment(score=percentage))


@span_decorator
def perform_reddit_transform_comment_thread_data(
    comment_thread_data: List[str],
) -> float:
    """
    This method does the actual work of generating a sentiment score from the
    comment thread data.

    Parameters
    ----------
    comment_thread_data : List[str]
        A list of comment thread data

    Returns
    -------
    float
       The sentiment score derived from the comment thread data.
    """
    POSITIVE_THRESHOLD = 0.1
    NEGATIVE_THRESHOLD = -0.1
    data = []
    for comment_text in comment_thread_data:
        score = perform_sentiment_analysis(comment_text)
        data.append(score)
    boolean_array = [
        True if val >= POSITIVE_THRESHOLD else False
        for val in data
        if val >= POSITIVE_THRESHOLD or val <= NEGATIVE_THRESHOLD
    ]
    true_count = sum(boolean_array)
    total_elements = len(boolean_array)
    percentage = (true_count / total_elements) * 100
    return percentage
