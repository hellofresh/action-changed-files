#!/usr/bin/env python3

import unittest
import neo


class TestChangedFiles(unittest.TestCase):
    def test_no_changes(self):
        self.assertFalse(
            neo.generate_matrix(
                include_regex="clusters/.*", changed_files=["clusters", "blah"]
            )
        )

    def test_changes_groups_level1(self):
        self.assertCountEqual(
            neo.generate_matrix(
                include_regex="clusters/(?P<environment>\w+)/.*",
                changed_files=[
                    "clusters/staging/app",
                    "clusters/staging/demo",
                    "clusters/live/app",
                ],
            ),
            [{"environment": "staging"}, {"environment": "live"}],
        )

    def test_changes_groups_level2(self):
        self.assertCountEqual(
            neo.generate_matrix(
                include_regex="clusters/(?P<environment>\w+)/(?P<namespace>\w+)",
                changed_files=[
                    "clusters/staging/app",
                    "clusters/live/app",
                    "clusters/staging/demo",
                ],
            ),
            [
                {"environment": "staging", "namespace": "app"},
                {"environment": "staging", "namespace": "demo"},
                {"environment": "live", "namespace": "app"},
            ],
        )

    def test_changes_no_group(self):
        self.assertCountEqual(
            neo.generate_matrix(
                include_regex="clusters/.*",
                changed_files=[
                    "clusters/staging/app",
                    "clusters/live/app",
                    "clusters/staging/demo",
                    "my_other_file/hello",
                ],
            ),
            [
                {"path": "clusters/staging/app"},
                {"path": "clusters/staging/demo"},
                {"path": "clusters/live/app"},
            ],
        )

    def test_changes_sorted(self):
        self.assertListEqual(
            neo.generate_matrix(
                include_regex="clusters/.*",
                changed_files=[
                    "my_other_file/hello",
                    "clusters/live/app",
                    "clusters/staging/app",
                    "clusters/staging/demo",
                ],
            ),
            [
                {"path": "clusters/live/app"},
                {"path": "clusters/staging/app"},
                {"path": "clusters/staging/demo"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
