import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _mcp_specifier(text: str) -> str:
    match = re.search(r'"?(mcp\[cli\][^"\n]*)', text)
    assert match is not None
    return match.group(1).rstrip(",")


def test_docker_requirements_match_pyproject_mcp_sdk_bounds():
    pyproject_specifier = _mcp_specifier((ROOT / "pyproject.toml").read_text())
    requirements_specifier = _mcp_specifier((ROOT / "requirements.txt").read_text())

    assert requirements_specifier == pyproject_specifier
    assert "<2.0.0" in requirements_specifier
