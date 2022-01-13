# action-changed-files

Generate a GitHub Actions job matrix based on changed files (with an extra twist).

## Problem statement

Repositories are often composed of multiple modules or directories that are built & deployed differently. They can represent a part of the system, or a specific environment. Modules like this also often share some common files.

The (traditional) and easiest way to guarantee that all changes are properly tested in CI is to run all jobs for every single change, but this can lead to a very long verification time.

Ideally, you want to be able to trigger (and skip) jobs based on the contents (and type) of a change.

[Trigger paths](https://docs.github.com/en/actions/learn-github-actions/workflow-syntax-for-github-actions#example-including-paths) and [matrix job strategy](https://docs.github.com/en/actions/learn-github-actions/workflow-syntax-for-github-actions#jobsjob_idstrategymatrix) are two great features that can help reducing verification time, but they're still not flexible enough.

## Example

### Sample repository

`neo` helps with generating a job matrix based on the changed files in a pull-request, or after merging it to the target branch.

Consider the following repository directory structure:

```
├── infrastructure
│   ├── live       # depends on terraform-modules
|   |── staging    # depends on terraform-modules
├── library
│   ├── common
│   ├── parser     # depends on library/common
│   ├── network    # depends on library/common
|── terraform-modules
|── deploy.sh      # used in CI to deploy infrastructure
|── Makefile       # used in CI to build library
```

and that we want to:

* verify & deploy changes to infrastructure as code affecting the `live` and `staging` environments
* build & test changes to `library/parser` and `library/network`

### Sample workflow

```yaml
name: Sample workflow

on:
  pull_request:
    branches:
      - master

jobs:
  neo:
    name: Generate job matrices
    id: generate-matrix
    runs-on: ubuntu-latest
    # don't forget to declare outputs here!
    outputs:
      matrix-infrastructure: ${{ steps.neo-infrastructure.outputs.matrix }}
      matrix-library: ${{ steps.neo-library.outputs.matrix }}
    steps:
      - name: Generate matrix | Infrastructure
        id: neo-infrastructure
        uses: hellofresh/action-changed-files
        with:
            pattern: infrastructure/(P<environment>[^/]+)
            default-patterns: |
                terraform-modules
                deploy.sh

      - name: Generate matrix | Library
        id: neo-library
        uses: hellofresh/action-changed-files
        with:
            pattern: library/(P<lib>(?!common)[^/]+)
            default-patterns: |
                library/common

  infrastructure:
    needs: [ generate-matrix ] # don't forget this!
    strategy:
      matrix: ${{ fromJson(needs.generate-matrix.outputs.matrix-infrastructure) }}
    if: ${{ fromJson(needs.generate-matrix.outputs.matrix-infrastructure).include[0] }} # skip if the matrix is empty!
    steps:
        - name: Deploy infrastructure
          run: echo "Deploying ${{ matrix.environment }}"

  build:
    needs: [ generate-matrix ]
    strategy:
      matrix: ${{ fromJson(needs.generate-matrix.outputs.matrix-build) }}
    if: ${{ fromJson(needs.generate-matrix.outputs.matrix-build).include[0] }}
    steps:
        - name: Building library
          run: echo "Building ${{ matrix.lib }}"
```

Let's break down what will happen here with a few examples:

<table>
    <tr>
        <th>Changed files</th>
        <th>Behaviour</th>
    </tr>
    <tr>
        <td>
            infrastructure/live/main.tf<br>
            infrastructure/staging/main.tf<br>
        </td>
         <td>
            jobs.deploy[live]<br>
            jobs.deploy[staging]<br>
        </td>
    </tr>
    <tr>
        <td>
            library/parser/json.c<br>
            library/network/tcp.c<br>
        </td>
         <td>
            jobs.build[parser]<br>
            jobs.build[network]<br>
        </td>
    </tr>
    <tr>
        <td>
            terraform-modules/aws.tf<br>
            library/common/printer.c<br>
        </td>
         <td>
            jobs.deploy[live]<br>
            jobs.deploy[staging]<br>
            jobs.build[parser]<br>
            jobs.build[network]<br>
        </td>
    </tr>
</table>


## Reference

<table>
    <tr>
        <th width="20%">Input parameter name</th>
        <th>Type</th>
        <th>Required</th>
        <th>Description</th>
    </tr>
    <tr>
        <td>pattern</td>
        <td>string</td>
        <td><b>yes</b></td>
        <td>
            Regular expression pattern with named groups. Changed files will be matched against this pattern and named groups will be extracted into the matrix. See <a href="https://docs.python.org/3/howto/regex.html#non-capturing-and-named-groups">the releveant section of the Python documentation</a> for the syntax reference.
        </td>
    </tr>
    <tr>
        <td>defaults</td>
        <td>boolean</td>
        <td>no</td>
        <td>
            if true, and no changed files match the pattern, recursively apply the pattern on all the files of the repository to generate a matrix of all possible combinations (a.k.a. run everything for changes to common files)
        </td>
    </tr>
    <tr>
        <td>default-patterns</td>
        <td>list[string]</td>
        <td>no</td>
        <td>
            similar to the 'defaults' flag, except we match changed files on the provided UNIX-style glob pattern
        </td>
    </tr>
    <tr>
        <td>ignore-deleted-files</td>
        <td>boolean</td>
        <td>no</td>
        <td>
            if true, ignore deleted files
        </td>
    </tr>
</table>