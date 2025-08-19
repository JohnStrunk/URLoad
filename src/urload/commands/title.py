"""Implements the 'title' command for URLoad."""

import textwrap
from typing import Any

from bs4 import BeautifulSoup

from urload.commands.base import Command, CommandError
from urload.url import URL


class TitleCommand(Command):
    """Retrieves and displays the HTML title from each URL in the list."""

    name = "title"
    description = textwrap.dedent("""
    title [[m]-[n]] - Retrieve and display HTML titles from URLs in the current list.

    This command fetches each URL, extracts the HTML title, and prints it with its index.
    If a range is specified (e.g., 0-4), it processes only those URLs.
    If no range is specified, it processes all URLs.
    """)

    def run(
        self, args: list[str], url_list: list[URL], settings: Any = None
    ) -> list[URL]:
        """
        Fetch HTML titles from URLs and print them with their index.

        :param args: Optional range argument (see command description).
        :param url_list: List of URL objects to process.
        :return: The original list (unmodified).
        :raises CommandError: If the argument is invalid.
        """

        def print_titles(start: int, end: int) -> None:
            if start < 0 or end < 0 or start > end or end >= len(url_list):
                raise CommandError("Invalid range argument.")
            for idx in range(start, end + 1):
                url = url_list[idx]
                try:
                    response = url.get()
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, "html.parser")
                    title_tag = soup.find("title")
                    title = (
                        title_tag.get_text().strip() if title_tag else "No title found"
                    )
                    print(f"{idx}: {title}")
                except Exception as e:
                    print(f"{idx}: Error fetching title - {e}")

        if not args:
            print_titles(0, len(url_list) - 1) if url_list else None
            return url_list

        arg = args[0]
        n = len(url_list)

        try:
            if "-" not in arg:  # Single index
                idx = int(arg)
                print_titles(idx, idx)
                return url_list
            if arg == "-":
                raise ValueError()
            if arg.startswith("-"):  # -N
                end = int(arg[1:])
                print_titles(0, end)
                return url_list
            if arg.endswith("-"):  # N-
                start = int(arg[:-1])
                print_titles(start, n - 1)
                return url_list
            # N-M
            start, end = map(int, arg.split("-", 1))
            print_titles(start, end)
            return url_list
        except ValueError:
            raise CommandError(
                "Invalid argument format. Use a single index or a range (e.g., N, -N, N-, N-M)."
            )
