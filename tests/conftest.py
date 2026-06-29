"""Shared pytest fixtures for the fork-questionnaire tool tests."""

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL_PATH = REPO_ROOT / "utils" / "fork_questionnaire_for_extract.py"
SOURCE_PHQ9 = REPO_ROOT / "CIRG-PHQ-9.json"
REPO_CSV = REPO_ROOT / "deploy-specific" / "mapping-input" / "CNICS PRO UCSD flowsheet FHIR IDs.csv"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_tool():
    """Import the tool module by file path (it lives in utils/, not a package)."""
    spec = importlib.util.spec_from_file_location(
        "fork_questionnaire_for_extract", TOOL_PATH
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def tool():
    """The imported fork_questionnaire_for_extract module."""
    return _load_tool()


@pytest.fixture
def phq9_copy(tmp_path):
    """A writable temp copy of the canonical CIRG-PHQ-9.json source."""
    dest = tmp_path / "CIRG-PHQ-9.json"
    shutil.copy(SOURCE_PHQ9, dest)
    return dest


@pytest.fixture
def repo_csv():
    """Path to the real flowsheet CSV in the repo."""
    return REPO_CSV


@pytest.fixture
def out_dirs(tmp_path):
    """A (uat_dir, prod_dir) pair under a temp directory."""
    return tmp_path / "uat", tmp_path / "prod"


@pytest.fixture
def fixtures_dir():
    """Path to the tests/fixtures directory."""
    return FIXTURES
