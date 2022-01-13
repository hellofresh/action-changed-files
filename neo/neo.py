#!/usr/bin/env python3

import os
import argparse
import glob
import fnmatch
import requests
import json
import logging
import re
from urllib.parse import quote_plus
from typing import List

from common import env_default, setup_logging
from requests.auth import HTTPBasicAuth


def generate_matrix(
    include_regex: str, changed_files: List[str], default=False, default_patterns=[]
):
    include_regex = re.compile(include_regex, re.M | re.S)

    # store all match objects
    matches = list(filter(None, (include_regex.match(f) for f in changed_files)))
    logging.debug("Got %d matches", len(matches))

    # check if changed files match the so-called default patterns
    matched_default_patterns = [
        pattern
        for pattern in default_patterns
        if fnmatch.filter(changed_files, pattern)
    ]

    if matched_default_patterns:
        logging.info("Files changed in defaults patterns %s", matched_default_patterns)

    # if nothing changed, list all files/directories
    if (not matches and default) or matched_default_patterns:
        logging.info("Listing all files/directories matching provided pattern")
        cwd = os.getenv("GITHUB_WORKSPACE", os.curdir)
        for path, _, files in os.walk(cwd):
            matches.extend(
                filter(
                    None,
                    (
                        include_regex.match(os.path.relpath(os.path.join(path, f), cwd))
                        for f in files
                    ),
                )
            )

    # transform matches into groups when applicable
    matrix = set()
    for match in matches:
        if match.groups():
            matrix.add(tuple(match.groupdict().items()))
        else:
            matrix.add(tuple([("path", match.string)]))

    # convert back to a dict (hashable, serializable)
    return [dict(tuple(e)) for e in matrix]


def main(args):
    session = requests.session()
    # see: https://docs.github.com/en/actions/security-guides/automatic-token-authentication
    if "CI" in os.environ:
        logging.debug("Using HTTP token authentication")
        session.headers["Authorization"] = f"token {args.github_token}"
    else:
        logging.debug("Using HTTP basic auth")
        session.auth = HTTPBasicAuth(args.github_username, args.github_token)

    r = session.get(
        f"https://api.github.com/repos/{args.github_repository}/compare/{quote_plus(args.github_base_ref)}...{quote_plus(args.github_head_ref)}"
    )
    r.raise_for_status()

    if args.ignore_deleted_files:
        changed_files = [
            e["filename"] for e in r.json().get("files", []) if e["status"] != "removed"
        ]
    else:
        changed_files = [e["filename"] for e in r.json().get("files", [])]

    logging.debug("Changed files from GitHub: %s", changed_files)

    matrix = generate_matrix(
        args.include_regex, changed_files, args.defaults, args.default_patterns
    )

    if os.getenv("GITHUB_ACTIONS"):
        logging.debug(f"Outputting a matrix of {len(matrix)} combinations")
        files_json = json.dumps({"include": matrix})
        print(f"::set-output name=matrix::{files_json}")
    else:
        logging.info("Would output matrix: %s", matrix)


def github_webhook_ref(dest: str, option_strings: list):
    github_event_name = os.getenv("GITHUB_EVENT_NAME", None)
    github_event_path = os.getenv("GITHUB_EVENT_PATH", None)
    is_github_head_ref = "--github-head-ref" in option_strings
    if github_event_path:
        with open(github_event_path, "r") as fp:
            github_event = json.load(fp)
            if github_event_name == "pull_request":
                return argparse.Action(
                    default=github_event["pull_request"]["head"]["ref"]
                    if is_github_head_ref
                    else github_event["pull_request"]["base"]["ref"],
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
        "--verbose", "-v", help="increase verbosity", action="store_true"
    )
    user_arg_group.add_argument(
        "--pattern",
        "-p",
        dest="include_regex",
        help="regex pattern to match changed files against",
        required=True,
    )
    user_arg_group.add_argument(
        "--ignore-deleted-files",
        help="ignore deleted files",
        type=bool,
        default="false",
    )
    user_arg_group.add_argument(
        "--defaults",
        "-d",
        help="if any changed files match this pattern, recursively match all files in the current directory with the include pattern (a.k.a. run everything)",
        type=bool,
    )
    user_arg_group.add_argument(
        "--default-patterns",
        help="if any changed files match this pattern, apply --defaults",
        nargs="+",
        default=os.getenv("DEFAULT_PATTERNS", "").splitlines()
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    main(args)
