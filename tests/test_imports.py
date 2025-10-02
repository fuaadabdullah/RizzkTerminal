"""Basic import smoke tests."""


def test_imports() -> None:
    import rizzk  # noqa: F401
    from rizzk.core import data, journal, news, settings, util  # noqa: F401

    assert hasattr(rizzk, "core")
