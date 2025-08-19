"""
URLoad interactive CLI main module.

This module provides the entry point for the URLoad application, an interactive
command-line tool for scraping websites with tab completion and history support.
"""

import atexit
import os
import re
import sys
from collections.abc import Generator, Iterable
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import InMemoryHistory

from urload.commands.add import AddCommand
from urload.commands.base import Command
from urload.commands.clear import ClearCommand
from urload.commands.delete import DeleteCommand
from urload.commands.discard import DiscardCommand
from urload.commands.exit import ExitCommand
from urload.commands.fileformat import FileformatCommand
from urload.commands.get import GetCommand
from urload.commands.get_option import GetOptionCommand
from urload.commands.head import HeadCommand
from urload.commands.help import HelpCommand
from urload.commands.href import HrefCommand
from urload.commands.img import ImgCommand
from urload.commands.keep import KeepCommand
from urload.commands.list import ListCommand
from urload.commands.load import LoadCommand
from urload.commands.save import SaveCommand
from urload.commands.set_option import SetOptionCommand
from urload.commands.sort import SortCommand
from urload.commands.tail import TailCommand
from urload.commands.timeformat import TimeformatCommand
from urload.commands.title import TitleCommand
from urload.commands.uniq import UniqCommand
from urload.settings import AppSettings
from urload.url import URL

HELP_ARG_COUNT = 2


class CommandCompleter(Completer):
    """Custom completer for URLoad commands.

    Only completes command names at the start of the line, or as the first argument to 'help'.
    """

    def __init__(self, commands: list[str]):
        """Initialize with a list of command names."""
        self.commands = commands

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Generator[Completion, None, None]:
        """Yield completions for command names at the start or as help argument."""
        text = document.text_before_cursor
        lstripped = text.lstrip()
        parts = lstripped.split()
        word = document.get_word_before_cursor(WORD=True)

        # Special case: 'help ' (with a space and no argument) should yield all completions
        if lstripped == "help ":
            yield from (Completion(cmd, start_position=0) for cmd in self.commands)
            return

        # If the input is exactly a command and a space, do not complete
        if any(lstripped == f"{cmd} " for cmd in self.commands):
            return

        # For help, if input is 'help <cmd> ', do not complete (but not for just 'help ')
        if (
            len(parts) == HELP_ARG_COUNT
            and parts[0] == "help"
            and lstripped.endswith(" ")
            and parts[1] in self.commands
            and parts[1] != ""
        ):
            return

        # Complete command names at the start or if only partial command is typed
        if not parts or (len(parts) == 1 and text.rstrip() == parts[0]):
            yield from (
                Completion(cmd, start_position=-len(word))
                for cmd in self.commands
                if cmd.startswith(word)
            )
            return

        # Complete command names as argument to help
        if parts[0] == "help":
            if len(parts) == 1:
                yield from (Completion(cmd, start_position=0) for cmd in self.commands)
            elif len(parts) == HELP_ARG_COUNT and text.rstrip().endswith(parts[1]):
                arg = word if len(parts) > 1 else ""
                yield from (
                    Completion(cmd, start_position=-len(arg))
                    for cmd in self.commands
                    if cmd.startswith(arg)
                )
            return
        # Otherwise, do not complete command names as arguments
        return


def build_command_objs() -> dict[str, Command]:
    """Build and return the command objects dictionary."""
    # All commands must be listed here to be available in the CLI
    # Keep this list sorted
    command_objs: dict[str, Command] = {}
    command_objs["add"] = AddCommand()
    command_objs["clear"] = ClearCommand()
    command_objs["del"] = DeleteCommand()
    command_objs["discard"] = DiscardCommand()
    command_objs["exit"] = ExitCommand()
    command_objs["fileformat"] = FileformatCommand()
    command_objs["get"] = GetCommand()
    command_objs["get-option"] = GetOptionCommand()
    command_objs["head"] = HeadCommand()
    command_objs["help"] = HelpCommand(command_objs)
    command_objs["href"] = HrefCommand()
    command_objs["img"] = ImgCommand()
    command_objs["keep"] = KeepCommand()
    command_objs["list"] = ListCommand()
    command_objs["load"] = LoadCommand()
    command_objs["save"] = SaveCommand()
    command_objs["set-option"] = SetOptionCommand()
    command_objs["sort"] = SortCommand()
    command_objs["tail"] = TailCommand()
    command_objs["timeformat"] = TimeformatCommand()
    command_objs["title"] = TitleCommand()
    command_objs["uniq"] = UniqCommand()
    return command_objs


def get_next_numeric_dir(base_path: str) -> int:
    """Return the next 4-digit numeric directory name in base_path, or 0 if none found."""
    max_num = -1
    for name in os.listdir(base_path):
        if os.path.isdir(os.path.join(base_path, name)) and re.fullmatch(
            r"\d{4}", name
        ):
            num = int(name)
            max_num = max(max_num, num)
    return max_num + 1


def handle_user_input(
    user_input: str,
    command_objs: dict[str, Command],
    url_list: list[URL],
    settings: AppSettings,
) -> list[URL]:
    """
    Process a single user input line and return the new url_list.

    Parses the input, executes the corresponding command if found, and returns the updated URL list.

    :param user_input: The command line input from the user
    :param command_objs: Dictionary of command names to Command objects
    :param url_list: Current list of URLs
    :param settings: Application settings
    :return: The updated url_list after command execution
    :raises SystemExit: If an 'exit' command or similar causes the CLI to exit.
    """
    parts = user_input.strip().split()
    if not parts:
        return url_list
    cmd, *args = parts
    if cmd in command_objs:
        try:
            return command_objs[cmd].run(args, url_list, settings)
        except SystemExit:
            raise
        except Exception as e:
            print(e)
            return url_list
    else:
        print(f"Unknown command: {cmd}")
        return url_list


def execute_commands_from_source(
    source: Iterable[str],
    command_objs: dict[str, Command],
    url_list: list[URL],
    settings: AppSettings,
) -> tuple[list[URL], bool]:
    """
    Execute commands from a file-like source, line by line.

    Each line is processed as a command. If a SystemExit is raised (e.g., by an 'exit' command),
    the function returns immediately.

    :param source: Iterable of command strings to execute
    :param command_objs: Dictionary of command names to Command objects
    :param url_list: Current list of URLs
    :param settings: Application settings
    :return: Updated url_list and a boolean indicating if a SystemExit was raised
    :raises SystemExit: If an 'exit' command or similar causes the CLI to exit.
    """
    for line in source:
        stripped_line: str = line.strip()
        if stripped_line:
            try:
                url_list = handle_user_input(
                    stripped_line, command_objs, url_list, settings
                )
            except SystemExit:
                return url_list, True
    return url_list, False


def main() -> None:
    """
    Entry point for the URLoad interactive CLI application.

    Provides a prompt with tab completion and history support.
    """
    url_list: list[URL] = []
    settings = AppSettings.load()

    # Determine session directory
    session_base = os.getcwd()
    settings.session_dir_num = get_next_numeric_dir(session_base)

    command_objs = build_command_objs()
    completer = CommandCompleter(list(command_objs.keys()))
    history: InMemoryHistory = InMemoryHistory()
    session: PromptSession[Any] = PromptSession(completer=completer, history=history)
    atexit.register(settings.save)
    print("Welcome to URLoad! Type 'help' for commands.")
    print(f"Current session directory: {settings.session_dir_num:04d}")

    # Process command files if provided as arguments
    exited = False
    if len(sys.argv) > 1:
        for filename in sys.argv[1:]:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    url_list, exited = execute_commands_from_source(
                        f, command_objs, url_list, settings
                    )
                    if exited:
                        return
            except Exception as e:
                print(f"Error reading file '{filename}': {e}")

    # Enter interactive mode
    while not exited:
        try:
            prompt_str = f"URLoad ({len(url_list)}) > "
            user_input = session.prompt(prompt_str)
            url_list, exited = execute_commands_from_source(
                [user_input], command_objs, url_list, settings
            )
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
