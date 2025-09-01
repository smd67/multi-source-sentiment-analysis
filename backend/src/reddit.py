import os
import praw
import random
from typing import List, Tuple, Generator  # pylint: disable=import-error
from praw.models import MoreComments
from model import ( # pylint: disable=import-error
    ChainType,
    TargetQuery,
    Sentiment,
) 
from common import perform_sentiment_analysis, get_secret  # pylint: disable=import-error
from bonobo.config import use


@use("query")
def reddit_extract_search_data(
    query: TargetQuery,
) -> Generator[List[str], None, None]:
    MAX_RESULTS = 100
    search_data = []
    client_id = get_secret("REDDIT_CLIENT_ID")
    client_secret = get_secret("REDDIT_CLIENT_SECRET")
    user_agent = "sdimig-user-agent"
    reddit = praw.Reddit(
        client_id=client_id, client_secret=client_secret, user_agent=user_agent
    )
    subreddit = reddit.subreddit("AskReddit")
    for submission in subreddit.search(query.target, limit=MAX_RESULTS):
        search_data.append(submission)
    yield search_data


def reddit_extract_comment_thread_data(
    search_data: List[str],
) -> Generator[List[str], None, None]:
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
    yield comment_thread_data


def reddit_transform_comment_thread_data(
    comment_thread_data: List[str],
) -> Generator[Tuple[ChainType, Sentiment], None, None]:
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
    yield (ChainType.REDDIT_SENTIMENT_DATA, Sentiment(score=percentage))
