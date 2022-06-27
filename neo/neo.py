#!/usr/bin/env python3

from collections import defaultdict
import os
import argparse
import glob
import fnmatch
import requests
import json
import re
from urllib.parse import quote_plus
from typing import List

from common import env_default, hdict, strtobool
from requests.auth import HTTPBasicAuth


def generate_matrix(
    files: dict, include_regex: str, defaults=False, default_patterns=[], default_dir=os.getenv("GITHUB_WORKSPACE", os.curdir)
):
    include_regex = re.compile(include_regex, re.M | re.S)

    changed_files = [(e["filename"], e["status"]) for e in files]
    matches = defaultdict(set)

    def update_matches(files: List[str]):
        for (filename, status) in files:
            match = include_regex.match(filename)
            if match:
                if match.groupdict():
                    if "reason" in match.groupdict().keys():
                        raise ValueError("reason is a reserved name for the job matrix")
                    key = hdict(match.groupdict())
                else:
                    key = hdict({"path": filename})
                matches[key].add(status)

    update_matches(changed_files)

    # check if changed files match the so-called default patterns
    matched_default_patterns = [
        pattern
        for pattern in default_patterns
        if fnmatch.filter((c for c, _ in changed_files), pattern)
    ]

    if matched_default_patterns:
        print("Files changed in defaults patterns: ", matched_default_patterns)

    # if nothing changed, list all files/directories
    if (not matches and defaults) or matched_default_patterns:
        print(
            "Listing all files/directories in repository matching the provided pattern"
        )
        default_files = [(os.path.relpath(os.path.join(path, f), default_dir), "default") for path, _, files in os.walk(default_dir) for f in files]
        update_matches(default_files)

    # mark matrix entries with a status if all its matches have the same status
    matrix = []
    for (groups, statuses) in matches.items():
        groups["reason"] = statuses.pop() if len(statuses) == 1 else "updated"
        matrix.append(groups)

    # convert back to a dict (hashable, serializable)
    return sorted(matrix)


def main(args):
    session = requests.session()
    session.hooks = {
        "response": lambda r, *args, **kwargs: r.raise_for_status()
    }
    # see: https://docs.github.com/en/actions/security-guides/automatic-token-authentication
    if "CI" in os.environ:
        session.headers["Authorization"] = f"token {args.github_token}"
    else:
        session.auth = HTTPBasicAuth(args.github_username, args.github_token)

    url = f"https://api.github.com/repos/{args.github_repository}/compare/{quote_plus(args.github_base_ref)}...{quote_plus(args.github_head_ref)}"
    print("GitHub API request: ", url)

    r = session.get(url)
    files = r.json().get("files", [])
    while link := r.links.get("next"):
        next_page_url = link["url"]
        print(f"Loading next page: {next_page_url}")
        r = session.get(next_page_url)
        files.extend(r.json().get("files", []))

    matrix = generate_matrix(
        files, args.include_regex, args.defaults, args.default_patterns
    )

    print("Generated matrix: ", matrix)

    if os.getenv("GITHUB_ACTIONS"):
        files_json = json.dumps({"include": matrix})
        print(f"::set-output name=matrix::{files_json}")


def github_webhook_ref(dest: str, option_strings: list):
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    github_arg_group = parser.add_argument_group("github environment")
    github_arg_group.add_argument(
        "--github-repository", action=env_default("GITHUB_REPOSITORY"), required=True
    )

    github_arg_group.add_argument(
        "--github-token", action=env_default("GITHUB_TOKEN"), required=True
    )
    github_arg_group.add_argument(
        "--github-username",
        help="provide this argument if testing locally",
        required=False,
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
        "--ignore-deleted-files",
        help="ignore deleted files",
        type=strtobool,
        default="false",
    )
    user_arg_group.add_argument(
        "--defaults",
        help="if any changed files match this pattern, recursively match all files in the current directory with the include pattern (a.k.a. run everything)",
        type=strtobool,
        default="false",
    )
    user_arg_group.add_argument(
        "--default-patterns",
        help="if any changed files match this pattern, apply --defaults",
        nargs="+",
        default=os.getenv("DEFAULT_PATTERNS", "").splitlines(),
    )

    args = parser.parse_args()
    main(args)
