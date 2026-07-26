from src.validators.imdb import _find_all_imdb_ids, extract_imdb_id

# --- Happy path ---


def test_extracts_bare_imdb_id() -> None:
    assert extract_imdb_id("tt1234567") == "tt1234567"


def test_extracts_8_digit_id() -> None:
    assert extract_imdb_id("tt12345678") == "tt12345678"


def test_extracts_id_embedded_in_text() -> None:
    assert extract_imdb_id("please add tt1234567 thanks") == "tt1234567"


def test_extracts_id_with_surrounding_punctuation() -> None:
    assert extract_imdb_id("add: tt1234567!") == "tt1234567"


# --- Case handling ---


def test_extracts_uppercase_prefix() -> None:
    assert extract_imdb_id("TT1234567") == "tt1234567"


def test_extracts_mixed_case() -> None:
    assert extract_imdb_id("Tt1234567") == "tt1234567"


# --- Edge cases ---


def test_returns_none_for_no_id() -> None:
    assert extract_imdb_id("hello world") is None


def test_returns_none_for_empty_string() -> None:
    assert extract_imdb_id("") is None


def test_returns_none_for_too_few_digits() -> None:
    assert extract_imdb_id("tt123456") is None


def test_returns_none_for_too_many_digits() -> None:
    assert extract_imdb_id("tt123456789") is None


def test_returns_none_for_non_digit_suffix() -> None:
    assert extract_imdb_id("ttabcdefg") is None


def test_returns_none_for_tt_without_digits() -> None:
    assert extract_imdb_id("just tt here") is None


def test_extracts_id_at_start_of_line() -> None:
    assert extract_imdb_id("tt1234567 is the one") == "tt1234567"


def test_extracts_id_at_end_of_line() -> None:
    assert extract_imdb_id("the id is tt1234567") == "tt1234567"


# --- Multiple IDs ---


def test_extracts_first_when_multiple_present() -> None:
    assert extract_imdb_id("tt1234567 and tt7654321") == "tt1234567"


# --- Newline edge ---


def test_extracts_id_after_newline() -> None:
    assert extract_imdb_id("add\n\ntt1234567") == "tt1234567"


# --- Internal helper ---


def test_find_all_returns_all_unique_ids() -> None:
    result = _find_all_imdb_ids("tt1234567 tt7654321")
    assert sorted(result) == ["tt1234567", "tt7654321"]


def test_find_all_deduplicates() -> None:
    result = _find_all_imdb_ids("tt1234567 tt1234567")
    assert result == ["tt1234567"]
