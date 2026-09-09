# Release and Versioning Process

The project follows Semantic Versioning. Each documented version describes
capabilities delivered by the repository at that release boundary.

| Version | Delivered scope |
| --- | --- |
| `v0.1.0` | Static analytical MVP |

Changes are developed on focused branches, reviewed through pull requests, and
merged to `main` after required CI checks pass.

To prepare a release:

1. Confirm that the selected commit is on `main` and required CI checks pass.
2. Update the project version and changelog.
3. Create an annotated version tag from the reviewed commit.
4. Publish the tag and create release notes that summarize the delivered changes.

Release notes link to the changelog, relevant architecture documentation, and
available CI or runtime evidence.
