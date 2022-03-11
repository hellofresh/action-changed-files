#!/usr/bin/env python3

import unittest
import neo


class TestChangedFiles(unittest.TestCase):
    def test_no_changes(self):
        self.assertFalse(
            neo.generate_matrix(
                include_regex="clusters/.*", payload={
                    "files": [
                        {"filename": "clusters", "status": "changed"},
                        {"filename": "blah", "status": "changed"}
                    ]
                }
            )
        )

    def test_changes_groups_level1(self):
        self.assertCountEqual(
            neo.generate_matrix(
                include_regex="clusters/(?P<environment>\w+)/.*",
                payload={
                    "files": [
                        {"filename": "clusters/staging/app", "status": "changed"},
                        {"filename": "clusters/staging/demo", "status": "changed"},
                        {"filename": "clusters/live/app", "status": "changed"},
                    ]
                }
            ),
            [{"environment": "staging"}, {"environment": "live"}],
        )

    def test_changes_groups_level2(self):
        self.assertCountEqual(
            neo.generate_matrix(
                include_regex="clusters/(?P<environment>\w+)/(?P<namespace>\w+)",
                payload={
                    "files": [
                        {"filename": "clusters/staging/app", "status": "changed"},
                        {"filename": "clusters/live/app", "status": "changed"},
                        {"filename": "clusters/staging/demo", "status": "changed"},
                    ]
                }
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
                payload={
                    "files": [
                        {"filename": "clusters/staging/app", "status": "changed"},
                        {"filename": "clusters/live/app", "status": "changed"},
                        {"filename": "clusters/staging/demo", "status": "changed"},
                        {"filename": "my_other_file/hello", "status": "changed"},
                    ]
                }
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
                payload={
                    "files": [
                        {"filename": "my_other_file/hello", "status": "changed"},
                        {"filename": "clusters/live/app", "status": "changed"},
                        {"filename": "clusters/staging/app", "status": "changed"},
                        {"filename": "clusters/staging/demo", "status": "changed"},
                    ]
                },
            ),
            [
                {"path": "clusters/live/app"},
                {"path": "clusters/staging/app"},
                {"path": "clusters/staging/demo"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
