"""
Playwright driver that executes operations based on a profile.
"""

import argparse
import random
import time

from playwright.sync_api import sync_playwright


def main(n: int, profile: str):
    """
    Main processing method.

    Parameters
    ----------
    profile : str
        Name of the file containgin the JSON formatted profile.
    """

    url = "http://localhost:10005"

    search_list = []
    with open(profile, 'r') as file:
        for line in file:
            search_list.append(line)

    # Open playwright and goto url
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)

        for i in range(n):
            target = random.choice(search_list)
            print(f"target={target}")
            page.locator("#multi-threaded").check()

            page.locator("input.my-input").fill(target)
            page.locator("button.my-button").click()
            time.sleep(180)
        browser.close()
        
        
if __name__ == "__main__":

    # 1. Create an ArgumentParser object
    parser = argparse.ArgumentParser(
        description="A simple traffic generator using web automation"
    )

    # 2. Add arguments
    parser.add_argument("-n", type=int, help="number of executions")
    parser.add_argument("--profile", type=str, help="The traffic profile containing a list of target searches")

    # 3. Parse the arguments
    args = parser.parse_args()

    # 4. Invoke main method
    main(args.n, args.profile)
