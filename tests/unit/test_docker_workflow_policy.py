from pathlib import Path


WORKFLOW = Path(__file__).parents[2] / ".github" / "workflows" / "docker-build.yml"


def test_docker_publish_events_and_tags_remain_explicit():
    workflow = WORKFLOW.read_text()

    assert "branches:\n      - main\n      - develop" in workflow
    assert "tags:\n      - 'v*'" in workflow
    assert "pull_request:\n    branches:\n      - main" in workflow
    assert "latest=false" in workflow

    # Branch and release tags are intentionally distinct; a PR must never publish.
    assert "enable=${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}" in workflow
    assert "enable=${{ github.event_name == 'push' && github.ref == 'refs/heads/develop' }}" in workflow
    assert "enable=${{ startsWith(github.ref, 'refs/tags/v') }}" in workflow
    assert "push: ${{ github.event_name == 'push'" in workflow
