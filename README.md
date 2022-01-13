# action-changed-files

Generate a GitHub Actions job matrix based on changed files (with an extra twist).

## Problem statement

Repositories are often composed of multiple modules or directories that are built & deployed differently. They can represent a part of the system, or a specific environment.

Modules like this also often share a common path.

The best way to guarantee that all changes are properly tested is to build, test/validate the entire repository in CI, but this can lead to a very long verification time.

[Including paths](https://docs.github.com/en/actions/learn-github-actions/workflow-syntax-for-github-actions#example-including-paths) and [matrix job strategy](https://docs.github.com/en/actions/learn-github-actions/workflow-syntax-for-github-actions#jobsjob_idstrategymatrix) are two great features that can help reducing verification time, but they're still not flexible enough.

## Why is this useful?

`neo` helps with generating a job matrix based on the changed files in a pull-request, or after merging it to the target branch.

Consider the following repository structure:

```
├── infrastructure
│   ├── live
|   |── staging
├── library
│   ├── common
│   ├── feature-1
│   ├── feature-2
|── terraform
├── LICENSE
└── README.md

```

with the following characteristics:

* `infrastructure` depends on the root `terraform` directory.
* both `library/feature-1` and `library/feature-2` depend on the `library/common` directory.

and that we want to:

* verify & deploy changes to infrastructure as code when files change in `infrastructure/live`, `infrastructure/staging` and `terraform`
* build & test changes to `library/feature-1` and `library/feature-2`