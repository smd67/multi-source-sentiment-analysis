import os
from nltk.sentiment import SentimentIntensityAnalyzer


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
    sentiment_score = sid.polarity_scores(text)["compound"]
    return sentiment_score

def get_secret(key: str) -> str:
    # Check for _FILE suffix first
    file_env = f"{key}_FILE"
    if file_env in os.environ:
        print(f"file_env={file_env}")
        with open(os.environ[file_env], 'r') as f:
            return f.read().strip()
    # Fall back to environment variable
    return os.environ.get(key)