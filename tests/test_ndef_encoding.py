from src.master_nfc_writer import normalize_record, make_ndef_uri_message, make_ndef_text_message


def test_normalize_url_adds_https():
    record_type, value = normalize_record("url", "example.com")
    assert record_type == "url"
    assert value == "https://example.com"


def test_make_uri_record():
    msg = make_ndef_uri_message("https://example.com")
    assert msg[0] == 0xD1
    assert msg[3] == 0x55


def test_make_text_record():
    msg = make_ndef_text_message("hello")
    assert msg[0] == 0xD1
    assert msg[3] == 0x54
