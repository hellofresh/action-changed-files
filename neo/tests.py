#!/usr/bin/env python3
import neo

import unittest
import os
import tempfile
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


if __name__ == "__main__":
    unittest.main()
