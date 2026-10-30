import pytest

from app.core.config import Settings


def test_missing_app_env_is_treated_as_production(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None)


def test_development_tolerates_dev_secrets(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    assert not Settings(_env_file=None).is_production
