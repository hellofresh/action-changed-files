#!/usr/bin/env python3
import neo

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path


class TestChangedFiles(unittest.TestCase):
    def test_no_changes(self):
        self.assertFalse(
            neo.generate_matrix(
                include_regex="clusters/.*",
                files=[
                    {"filename": "clusters", "status": "modified"},
                    {"filename": "blah", "status": "modified"},
                ],
            )
        )

    def test_no_changes_with_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            Path(os.path.join(d, "staging.txt")).touch()
            Path(os.path.join(d, "live.txt")).touch()
            self.assertCountEqual(
                neo.generate_matrix(
                    include_regex="(?P<environment>staging|live)",
                    defaults=True,
                    default_dir=d,
                    files=[
                        {"filename": "clusters", "status": "modified"},
                        {"filename": "blah", "status": "modified"},
                    ],
                ),
                [
                    {"environment": "staging", "reason": "default"},
                    {"environment": "live", "reason": "default"},
                ],
            )

    def test_changes_groups_level1(self):
        self.assertCountEqual(
            neo.generate_matrix(
                include_regex="clusters/(?P<environment>\w+)/.*",
                files=[
                    {"filename": "clusters/staging/app", "status": "modified"},
                    {"filename": "clusters/staging/demo", "status": "modified"},
                    {"filename": "clusters/live/app", "status": "modified"},
                ],
            ),
            [
                {"environment": "staging", "reason": "modified"},
                {"environment": "live", "reason": "modified"},
            ],
        )

    def test_changes_groups_level2(self):
        self.assertCountEqual(
            neo.generate_matrix(
                include_regex="clusters/(?P<environment>\w+)/(?P<namespace>\w+)",
                files=[
                    {"filename": "clusters/staging/app", "status": "modified"},
                    {"filename": "clusters/live/app", "status": "modified"},
                    {"filename": "clusters/staging/demo", "status": "modified"},
                ],
            ),
            [
                {"environment": "staging", "namespace": "app", "reason": "modified"},
                {"environment": "staging", "namespace": "demo", "reason": "modified"},
                {"environment": "live", "namespace": "app", "reason": "modified"},
            ],
        )

    def test_changes_no_group(self):
        self.assertCountEqual(
            neo.generate_matrix(
                include_regex="clusters/.*",
                files=[
                    {"filename": "clusters/staging/app", "status": "modified"},
                    {"filename": "clusters/live/app", "status": "modified"},
                    {"filename": "clusters/staging/demo", "status": "modified"},
                    {"filename": "my_other_file/hello", "status": "modified"},
                ],
            ),
            [
                {"path": "clusters/staging/app", "reason": "modified"},
                {"path": "clusters/staging/demo", "reason": "modified"},
                {"path": "clusters/live/app", "reason": "modified"},
            ],
        )

    def test_changes_sorted(self):
        self.assertListEqual(
            neo.generate_matrix(
                include_regex="clusters/.*",
                files=[
                    {"filename": "my_other_file/hello", "status": "modified"},
                    {"filename": "clusters/live/app", "status": "modified"},
                    {"filename": "clusters/staging/app", "status": "modified"},
                    {"filename": "clusters/staging/demo", "status": "modified"},
                ],
            ),
            [
                {"path": "clusters/live/app", "reason": "modified"},
                {"path": "clusters/staging/app", "reason": "modified"},
                {"path": "clusters/staging/demo", "reason": "modified"},
            ],
        )

    def test_all_matches_removed(self):
        self.assertCountEqual(
            neo.generate_matrix(
                include_regex="clusters/(?P<environment>\w+)/.*",
                files=[
                    {"filename": "clusters/staging/app", "status": "removed"},
                    {"filename": "clusters/staging/demo", "status": "removed"},
                    {"filename": "clusters/live/app", "status": "modified"},
                ],
            ),
            [
                {"environment": "staging", "reason": "removed"},
                {"environment": "live", "reason": "modified"},
            ],
        )

    def test_one_match_removed(self):
        self.assertCountEqual(
            neo.generate_matrix(
                include_regex="clusters/(?P<environment>\w+)/.*",
                files=[
                    {"filename": "clusters/staging/app", "status": "removed"},
                    {"filename": "clusters/staging/demo", "status": "modified"},
                    {"filename": "clusters/live/app", "status": "modified"},
                ],
            ),
            [
                {"environment": "staging", "reason": "updated"},
                {"environment": "live", "reason": "modified"},
            ],
        )

    def test_github_outputs(self):
        matrix = neo.generate_matrix(
            include_regex="clusters/.*",
            files=[
                {"filename": "clusters/staging/app", "status": "modified"},
                {"filename": "clusters/live/app", "status": "modified"},
                {"filename": "clusters/staging/demo", "status": "modified"},
                {"filename": "my_other_file/hello", "status": "modified"},
            ]
        )

        with contextlib.redirect_stdout(io.StringIO()) as f:
            neo.set_github_actions_output(matrix)

        output = f.getvalue()
        expected_matrix_output = json.dumps({"include": matrix})
        self.assertEqual(
            f"""::set-output name=matrix::{expected_matrix_output}
::set-output name=matrix-length::3\n""",
            output,
        )


class IntegrationTest(unittest.TestCase):
    empty_repo_commit_sha = "6b5794416e6750d16fb126a04eadb681349e6947"
    initial_import_commit_sha = "191fe221420a833dc9a43d3338c1d94ccab94ea6"

    def test_basic(self):
        matrix = neo.main(
            os.getenv("GITHUB_TOKEN"),
            "hellofresh/action-changed-files",
            self.empty_repo_commit_sha,
            self.initial_import_commit_sha,
            ".*",
        )
        self.assertEqual(len(matrix), 5)

    def test_pagination(self):
        unpaginated_result = neo.main(
            os.getenv("GITHUB_TOKEN"),
            "hellofresh/action-changed-files",
            self.empty_repo_commit_sha,
            self.initial_import_commit_sha,
            ".*",
        )
        paginated_result = neo.main(
            os.getenv("GITHUB_TOKEN"),
            "hellofresh/action-changed-files",
            self.empty_repo_commit_sha,
            self.initial_import_commit_sha,
            ".*",
            per_page=1,
        )
        self.assertListEqual(unpaginated_result, paginated_result)


if __name__ == "__main__":
    unittest.main()
