# Development

Dependencies are managed with [poetry](https://python-poetry.org/): `poetry install`

Tests are run with `./runtests`

## Releasing

CI handles releasing to PyPI.
Releases on GitHub are created manually.

Here's how to do a release:

 - Get all the desired changes into `master`
 - Wait for CI to pass that
 - Add a bump commit (see previous "Declare vX.Y.Z" commits; `poetry version` may be useful here)
 - Push that commit on master
 - Create a tag of that version number (`git tag v$(poetry version --short)`)
 - Push the tag (`git push --tags`)
 - CI will build & deploy that release
 - Create a Release on GitHub, ideally with a summary of changes
