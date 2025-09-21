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
    search_data = []
    query = SERVICES["query"]
    search_data = perform_reddit_extract_search_data(query)
    yield search_data


@span_decorator
def perform_reddit_extract_search_data(query: TargetQuery):
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
    yield perform_reddit_extract_comment_thread_data(search_data)


@span_decorator
def perform_reddit_extract_comment_thread_data(
    search_data: List[str],
) -> List[Any]:
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
    percentage = perform_reddit_transform_comment_thread_data(
        comment_thread_data
    )
    yield (ChainType.REDDIT_SENTIMENT_DATA, Sentiment(score=percentage))


@span_decorator
def perform_reddit_transform_comment_thread_data(
    comment_thread_data: List[str],
) -> float:
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
