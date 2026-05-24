#!/usr/bin/env python3

from collections import defaultdict
import os
import argparse
import fnmatch
import logging
import requests
import json
import re
from urllib.parse import quote_plus

from common import env_default, hdict, strtobool


def update_matches(files, include_regex, old_matches=defaultdict(set), ):
    """
    The update_matches function takes a list of files and their statuses,
    and returns a dictionary mapping the job matrix keys to sets of statuses.
    For example:

    :param old_matches: old matches object to update
    :param files: Store the files that are found in the directory
    :param include_regex: Filter the files that are included in the job matrix
    :return: A dictionary of dictionaries
    """
    matches = defaultdict(set)
    for (filename, status) in files:
        match = include_regex.match(filename)
        if match:
            if match.groupdict():
                if "reason" in match.groupdict().keys():
                    raise ValueError("reason is a reserved name for the job matrix")
                key = hdict(match.groupdict())
            else:
                key = hdict({"path": filename})
            if key in list(old_matches.keys()):
                status = old_matches.pop(key).pop()
            matches[key].add(status)

    return matches


def generate_matrix(
    files: list,
    include_regex: str,
    defaults: bool = False,
    default_patterns: list = None,
    default_dir: str = os.getenv("GITHUB_WORKSPACE", os.curdir),
) -> list:
    """
    The generate_matrix function takes a list of files and returns a matrix of
    files that match the provided pattern. The function also takes an optional
    include_regex parameter which is used to filter out unwanted files. If no
    include_regex is provided, all changed files are included in the matrix.

    :param files: Pass in the list of files that were changed
    :param include_regex:str: Indicate that the regex should be matched against the filename,
    Filter the files that are included in the matrix Define the pattern that is used to filter the files
    :param defaults: Determine if the default patterns should be used
    :param default_patterns: Provide a list of default patterns that will be used to determine
    if the matrix should be generated Define the pattern that is used to filter the files
    :param default_dir: Specify the root directory of the repository or use the current directory
    :return: A list of dictionaries
    """
    if default_patterns is None:
        default_patterns = []
    include_regex = re.compile(include_regex, re.M | re.S)
    changed_files = [(e["filename"], e["status"]) for e in files]

    # check if changed files match the so-called default patterns
    matched_default_patterns = [
        pattern
        for pattern in default_patterns
        if fnmatch.filter((c for c, _ in changed_files), pattern)
    ]

    if matched_default_patterns:
        logging.info("Files changed in defaults patterns: %s", matched_default_patterns)

    matches = update_matches(changed_files, include_regex)

    # if nothing changed, list all files/directories
    if (not matches and defaults) or matched_default_patterns:
        logging.info(
            "Listing all files/directories in repository matching the provided pattern"
        )
        default_files = [
            (os.path.relpath(os.path.join(path, f), default_dir), "default")
            for path, _, files in os.walk(default_dir)
            for f in files
        ]
        matches = update_matches( default_files, include_regex, matches)
    # mark matrix entries with a status if all its matches have the same status
    status_matrix = []
    for (groups, statuses) in matches.items():
        groups["reason"] = statuses.pop() if len(statuses) == 1 else "updated"
        status_matrix.append(groups)

    # convert back to a dict (hashable, serializable)
    return sorted(status_matrix)


def main(
    github_token: str,
    github_repository: str,
    github_base_ref: str,
    github_head_ref: str,
    include_regex: str,
    defaults: bool = False,
    default_patterns: list = None,
    per_page: int = 0,
):

    if default_patterns is None:
        default_patterns = []
    with requests.session() as session:
        session.hooks = {
            "response": lambda resp, *resp_args, **kwargs: resp.raise_for_status()
        }
        # see: https://docs.github.com/en/actions/security-guides/automatic-token-authentication
        session.headers["Authorization"] = f"token {github_token}"
        if per_page:
            session.params = {"per_page": per_page}

        github_api_url = os.environ['GITHUB_API_URL']
        compare_url = (
            f"{github_api_url}/repos/{github_repository}"
            f"/compare/{quote_plus(github_base_ref)}...{quote_plus(github_head_ref)}"
        )
        logging.info(f"GitHub API request: {compare_url}")

        r = session.get(compare_url)
        files = r.json().get("files", [])
        while link := r.links.get("next"):
            next_page_url = link["url"]
            logging.info(f"Loading next page: {next_page_url}")
            r = session.get(next_page_url)
            files.extend(r.json().get("files", []))

    return generate_matrix(files, include_regex, defaults, default_patterns)


def github_webhook_ref(dest: str, option_strings: list):
    """
    The github_webhook_ref function is a helper function that returns an argparse.Action object
    that will extract the ref from either the head or base of a pull request, depending on whether
    the --github-head-ref option was passed to the program. If neither --github-head-ref nor
    --github-base-ref are passed, then this action will default to using the base ref.

    :param dest:str: Specify the name of the attribute to which
    :param option_strings:list: Determine the name of the argument
    :return: An action that will be used by the `github_arg_group`
    """
    github_event_name = os.getenv("GITHUB_EVENT_NAME", None)
    github_event_path = os.getenv("GITHUB_EVENT_PATH", None)
    is_github_head_ref = "--github-head-ref" in option_strings
    if github_event_path:
        with open(github_event_path, "r") as fp:
            github_event = json.load(fp)
            if github_event_name == "pull_request":
                return argparse.Action(
                    default=github_event["pull_request"]["head"]["sha"]
                    if is_github_head_ref
                    else github_event["pull_request"]["base"]["sha"],
                    required=False,
                    dest=dest,
                    option_strings=option_strings,
                )
            elif github_event_name == "push":
                return argparse.Action(
                    default=github_event["after"]
                    if is_github_head_ref
                    else github_event["before"],
                    required=False,
                    dest=dest,
                    option_strings=option_strings,
                )
            else:
                raise NotImplementedError(
                    f"unsupported github event {github_event_name}"
                )

    return argparse._StoreAction(
        required=True, dest=dest, option_strings=option_strings
    )


def set_github_actions_output(generated_matrix: list) -> None:
    """
    The set_github_actions_output function is used to generate the output for GitHub Actions.
    It takes in a list of dictionaries and prints out two environment variables: matrix, which contains
    the JSON representation of the matrix, and matrix-length, which contains an integer representing
    the number of rows in the matrix.

    :param generated_matrix:List[dict]: Pass the generated matrix to the function
    :return: The generated matrix in a format that can be used by the github actions workflow
    """
    files_json = json.dumps({"include": generated_matrix})
    print(f"matrix={files_json}")
    print(f"matrix-length={len(generated_matrix)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    github_arg_group = parser.add_argument_group("github environment")
    github_arg_group.add_argument(
        "--github-repository", action=env_default("GITHUB_REPOSITORY"), required=True
    )
    github_arg_group.add_argument(
        "--github-token", action=env_default("GITHUB_TOKEN"), required=True
    )
    github_arg_group.add_argument("--github-head-ref", action=github_webhook_ref)
    github_arg_group.add_argument("--github-base-ref", action=github_webhook_ref)

    user_arg_group = parser.add_argument_group("user-provided")
    user_arg_group.add_argument(
        "--pattern",
        dest="include_regex",
        help="regex pattern to match changed files against",
        required=True,
    )
    user_arg_group.add_argument(
        "--defaults",
        help="if any changed files match this pattern, recursively match all files in the current directory with the "
        "include pattern (a.k.a. run everything)",
        type=strtobool,
        default="false",
    )
    user_arg_group.add_argument(
        "--default-patterns",
        help="if any changed files match this pattern, apply --defaults",
        nargs="+",
        default=os.getenv("DEFAULT_PATTERNS", "").splitlines(),
    )

    args = vars(parser.parse_args())

    logging.basicConfig(
        level=logging.DEBUG
        if os.getenv("NEO_LOG_LEVEL", "INFO") == "DEBUG"
        else logging.INFO
    )

    matrix = main(**args)
    logging.info(matrix)

    if os.getenv("GITHUB_ACTIONS"):
        set_github_actions_output(matrix)
