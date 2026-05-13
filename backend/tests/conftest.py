import pytest


@pytest.fixture(autouse=True)
def use_mock_providers(monkeypatch):
    monkeypatch.setenv("ESSAY_OCR_PROVIDER", "mock")
    monkeypatch.setenv("ESSAY_GRADER_PROVIDER", "deterministic")
