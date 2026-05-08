from src.master_nfc_writer import (
    decode_ndef_message,
    extract_ndef_from_raw,
    make_mifare_classic_ndef_tlv_payload,
    make_ndef_text_message,
    make_ndef_uri_message,
    normalize_record,
)


def test_normalize_url_adds_https():
    record_type, value = normalize_record("url", "example.com")
    assert record_type == "uri"
    assert value == "https://example.com"


def test_normalize_phone_creates_tel_uri():
    record_type, value = normalize_record("phone", "234-238-3694")
    assert record_type == "uri"
    assert value == "tel:2342383694"


def test_normalize_email_creates_mailto_uri():
    record_type, value = normalize_record("email", "admin@example.com")
    assert record_type == "uri"
    assert value == "mailto:admin@example.com"


def test_make_uri_record():
    msg = make_ndef_uri_message("https://example.com")
    assert msg[0] == 0xD1
    assert msg[1] == 0x01
    assert msg[3] == 0x55
    decoded = decode_ndef_message(msg)
    assert decoded["type"] == "uri"
    assert decoded["value"] == "https://example.com"


def test_make_phone_uri_record():
    msg = make_ndef_uri_message("tel:2342383694")
    decoded = decode_ndef_message(msg)
    assert decoded["type"] == "uri"
    assert decoded["value"] == "tel:2342383694"


def test_make_text_record():
    msg = make_ndef_text_message("hello")
    assert msg[0] == 0xD1
    assert msg[3] == 0x54
    decoded = decode_ndef_message(msg)
    assert decoded["type"] == "text"
    assert decoded["value"] == "hello"
    assert decoded["language"] == "en"


def test_mifare_classic_tlv_payload_extracts_ndef():
    payload = make_mifare_classic_ndef_tlv_payload("url", "https://example.com")
    assert len(payload) % 16 == 0
    ndef = extract_ndef_from_raw(payload)
    decoded = decode_ndef_message(ndef)
    assert decoded["value"] == "https://example.com"
