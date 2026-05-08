#!/usr/bin/env python3
"""
ACR122U MIFARE Classic NDEF Tool v3

Built for:
- ACR122U NFC reader/writer
- MIFARE Classic 1K cards
- Phone-readable NFC business cards

v3 features:
- Business Card Mode
- Presets from config.json
- Batch writing
- Existing NDEF read before overwrite
- CSV write logs
- URL, phone, email, and text NDEF records

Safety:
Use only on blank cards or cards you own. Do not use this on access badges,
employee cards, hotel cards, transit cards, apartment/gate cards, gym cards,
or anything that controls access.
"""

from smartcard.System import readers
from smartcard.Exceptions import NoCardException, CardConnectionException
from smartcard.util import toHexString
from pathlib import Path
from datetime import datetime
import csv
import json
import time

APP_NAME = "ACR122U MIFARE Classic NDEF Tool v3"
CONFIG_FILE = Path("config.json")
LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "write_log.csv"

KEY_DEFAULT_FF = [0xFF] * 6
KEY_NFC_FORUM = [0xD3, 0xF7, 0xD3, 0xF7, 0xD3, 0xF7]
KEY_MAD_A = [0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5]
KEY_MAD_B = [0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xB5]
KEY_ZERO = [0x00] * 6

COMMON_KEYS = [
    ("DEFAULT_FF", KEY_DEFAULT_FF),
    ("NFC_FORUM", KEY_NFC_FORUM),
    ("MAD_A", KEY_MAD_A),
    ("MAD_B", KEY_MAD_B),
    ("ZERO", KEY_ZERO),
]

KEY_TYPE_A = 0x60
KEY_TYPE_B = 0x61

DATA_BLOCKS_1K_ALL_NFC = [
    4, 5, 6,
    8, 9, 10,
    12, 13, 14,
    16, 17, 18,
    20, 21, 22,
    24, 25, 26,
    28, 29, 30,
    32, 33, 34,
    36, 37, 38,
    40, 41, 42,
    44, 45, 46,
    48, 49, 50,
    52, 53, 54,
    56, 57, 58,
    60, 61, 62,
]

MAD_BLOCK_1 = [
    0x14, 0x01, 0x03, 0xE1, 0x03, 0xE1, 0x03, 0xE1,
    0x03, 0xE1, 0x03, 0xE1, 0x03, 0xE1, 0x03, 0xE1
]
MAD_BLOCK_2 = [
    0x03, 0xE1, 0x03, 0xE1, 0x03, 0xE1, 0x03, 0xE1,
    0x03, 0xE1, 0x03, 0xE1, 0x03, 0xE1, 0x03, 0xE1
]

MAD_TRAILER = [
    0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5,
    0x78, 0x77, 0x88, 0xC1,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF
]

NFC_TRAILER = [
    0xD3, 0xF7, 0xD3, 0xF7, 0xD3, 0xF7,
    0x7F, 0x07, 0x88, 0x40,
    0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF
]

EMPTY_BLOCK = [0x00] * 16
EMPTY_NDEF_FIRST_BLOCK = [0x03, 0x00, 0xFE] + [0x00] * 13

DEFAULT_CONFIG = {
    "business_name": "Master of Repairs LLC",
    "owner_name": "Rick Browneagle",
    "default_url": "https://blinq.me/cmnuxghx600810as66v5d49ys?utm_medium=accessory",
    "website_url": "https://masterofrepairs.com",
    "phone": "234-238-3694",
    "email": "admin@masterofrepairs.com",
    "presets": [
        {"name": "Master of Repairs Blinq Card", "type": "url", "value": "https://blinq.me/cmnuxghx600810as66v5d49ys?utm_medium=accessory"},
        {"name": "Master of Repairs Website", "type": "url", "value": "https://masterofrepairs.com"},
        {"name": "Call Master of Repairs", "type": "phone", "value": "234-238-3694"},
        {"name": "Email Master of Repairs", "type": "email", "value": "admin@masterofrepairs.com"}
    ],
    "settings": {
        "require_confirmation_for_format": True,
        "require_confirmation_for_overwrite": True,
        "batch_delay_seconds_after_success": 1.0
    }
}

class NFCError(Exception):
    pass


def print_header(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def pause():
    input("\nPress Enter to continue...")


def yes_no(prompt, default=False):
    suffix = " [Y/n]: " if default else " [y/N]: "
    ans = input(prompt + suffix).strip().lower()
    if not ans:
        return default
    return ans in ("y", "yes")


def load_config():
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        return DEFAULT_CONFIG.copy()
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        print("Warning: config.json could not be loaded. Using defaults.")
        return DEFAULT_CONFIG.copy()

    merged = DEFAULT_CONFIG.copy()
    merged.update(cfg)
    settings = DEFAULT_CONFIG["settings"].copy()
    settings.update(merged.get("settings", {}))
    merged["settings"] = settings
    if not isinstance(merged.get("presets"), list):
        merged["presets"] = DEFAULT_CONFIG["presets"]
    return merged


CONFIG = load_config()


def save_config():
    CONFIG_FILE.write_text(json.dumps(CONFIG, indent=2), encoding="utf-8")


def ensure_log_file():
    LOG_DIR.mkdir(exist_ok=True)
    if not LOG_FILE.exists():
        with LOG_FILE.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "uid", "action", "record_type", "value", "result", "details"])


def log_write(uid, action, record_type, value, result, details=""):
    ensure_log_file()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now().isoformat(timespec="seconds"), uid, action, record_type, value, result, details])


def transmit(conn, apdu, label="APDU", require_success=True):
    data, sw1, sw2 = conn.transmit(apdu)
    if require_success and (sw1, sw2) != (0x90, 0x00):
        raise NFCError(f"{label} failed. SW={sw1:02X} {sw2:02X}")
    return data, sw1, sw2


def get_readers():
    return list(readers())


def pick_reader():
    found = get_readers()
    if not found:
        raise NFCError("No smart card readers found. Check ACR122U USB connection/driver.")

    print_header("Readers Found")
    for idx, reader in enumerate(found):
        print(f"[{idx}] {reader}")

    for idx, reader in enumerate(found):
        if "ACR122" in str(reader).upper() or "ACS" in str(reader).upper():
            print(f"\nSuggested reader: [{idx}] {reader}")
            break

    while True:
        choice = input("\nChoose reader number: ").strip()
        if choice.isdigit() and int(choice) in range(len(found)):
            return found[int(choice)]
        print("Invalid selection.")


def connect_card(reader):
    conn = reader.createConnection()
    conn.connect()
    return conn


def get_uid(conn):
    data, _, _ = transmit(conn, [0xFF, 0xCA, 0x00, 0x00, 0x00], "Get UID")
    return "".join(f"{b:02X}" for b in data)


def load_key_slot0(conn, key_bytes):
    transmit(conn, [0xFF, 0x82, 0x00, 0x00, 0x06] + key_bytes, "Load key slot 0")


def authenticate_with_key(conn, block, key_bytes, key_type=KEY_TYPE_A):
    load_key_slot0(conn, key_bytes)
    _, sw1, sw2 = transmit(
        conn,
        [0xFF, 0x86, 0x00, 0x00, 0x05, 0x01, 0x00, block, key_type, 0x00],
        f"Authenticate block {block}",
        require_success=False,
    )
    return (sw1, sw2) == (0x90, 0x00)


def authenticate_any(conn, block, preferred=None):
    candidates = preferred or COMMON_KEYS
    for key_type_name, key_type in [("A", KEY_TYPE_A), ("B", KEY_TYPE_B)]:
        for key_name, key in candidates:
            try:
                if authenticate_with_key(conn, block, key, key_type):
                    return {"ok": True, "key_name": key_name, "key_type": key_type_name, "key": key}
            except Exception:
                pass
    return {"ok": False}


def read_block(conn, block):
    data, _, _ = transmit(conn, [0xFF, 0xB0, 0x00, block, 0x10], f"Read block {block}")
    return list(data)


def is_sector_trailer(block):
    return block % 4 == 3


def write_block(conn, block, data16, allow_trailer=False):
    if len(data16) != 16:
        raise ValueError("MIFARE Classic write block must be exactly 16 bytes.")
    if block == 0:
        raise NFCError("Refusing to write manufacturer block 0.")
    if is_sector_trailer(block) and not allow_trailer:
        raise NFCError(f"Refusing to write trailer block {block} without allow_trailer=True.")
    transmit(conn, [0xFF, 0xD6, 0x00, block, 0x10] + list(data16), f"Write block {block}")


def sector_first_block(sector):
    return sector * 4


def sector_trailer_block(sector):
    return sector * 4 + 3


def data_blocks_for_sector(sector):
    first = sector_first_block(sector)
    return [first, first + 1, first + 2]


def clean_phone_for_uri(value):
    return "".join(c for c in value if c.isdigit() or c == "+")


def normalize_record(record_type, value):
    record_type = record_type.lower().strip()
    value = value.strip()
    if record_type == "url":
        if not (value.lower().startswith("http://") or value.lower().startswith("https://")):
            value = "https://" + value
        return "uri", value
    if record_type == "phone":
        phone = clean_phone_for_uri(value)
        if not phone:
            raise ValueError("Phone number cannot be empty.")
        return "uri", "tel:" + phone
    if record_type == "email":
        if not value:
            raise ValueError("Email cannot be empty.")
        return "uri", value if value.lower().startswith("mailto:") else "mailto:" + value
    if record_type == "text":
        if not value:
            raise ValueError("Text cannot be empty.")
        return "text", value
    if record_type == "uri":
        if not value:
            raise ValueError("URI cannot be empty.")
        return "uri", value
    raise ValueError(f"Unsupported record type: {record_type}")


def make_ndef_uri_message(uri):
    _, uri = normalize_record("uri", uri)
    prefixes = [
        ("https://www.", 0x02),
        ("http://www.", 0x01),
        ("https://", 0x04),
        ("http://", 0x03),
        ("tel:", 0x05),
        ("mailto:", 0x06),
    ]
    prefix_code = 0x00
    remainder = uri
    lower = uri.lower()
    for prefix, code in prefixes:
        if lower.startswith(prefix):
            prefix_code = code
            remainder = uri[len(prefix):]
            break
    payload = bytes([prefix_code]) + remainder.encode("utf-8")
    if len(payload) > 255:
        raise ValueError("URI payload is too large for this simple writer.")
    return bytes([0xD1, 0x01, len(payload), 0x55]) + payload


def make_ndef_text_message(text, language="en"):
    text = text.strip()
    if not text:
        raise ValueError("Text cannot be empty.")
    lang_bytes = language.encode("ascii")
    text_bytes = text.encode("utf-8")
    payload = bytes([len(lang_bytes)]) + lang_bytes + text_bytes
    if len(payload) > 255:
        raise ValueError("Text payload is too large for this simple writer.")
    return bytes([0xD1, 0x01, len(payload), 0x54]) + payload


def make_ndef_message(record_type, value):
    normalized_type, normalized_value = normalize_record(record_type, value)
    if normalized_type == "uri":
        return make_ndef_uri_message(normalized_value)
    if normalized_type == "text":
        return make_ndef_text_message(normalized_value)
    raise ValueError(f"Unsupported record type: {record_type}")


def make_mifare_classic_ndef_tlv_payload(record_type, value):
    ndef = make_ndef_message(record_type, value)
    tlv = bytes([0x00, 0x00, 0x03, len(ndef)]) + ndef + bytes([0xFE])
    padding = (16 - (len(tlv) % 16)) % 16
    return tlv + bytes([0x00] * padding)


def extract_ndef_from_raw(raw):
    i = 0
    while i < len(raw):
        t = raw[i]
        if t == 0x00:
            i += 1
            continue
        if t == 0xFE:
            return None
        if t == 0x03:
            if i + 1 >= len(raw):
                return None
            length = raw[i + 1]
            if length == 0xFF:
                if i + 3 >= len(raw):
                    return None
                length = (raw[i + 2] << 8) | raw[i + 3]
                start = i + 4
            else:
                start = i + 2
            return raw[start:start + length]
        if i + 1 >= len(raw):
            return None
        i += 2 + raw[i + 1]
    return None


def decode_ndef_message(ndef):
    if not ndef or len(ndef) < 4:
        return None
    type_len = ndef[1]
    payload_len = ndef[2]
    type_start = 3
    payload_start = type_start + type_len
    if len(ndef) < payload_start + payload_len:
        return None
    rec_type = ndef[type_start:payload_start]
    payload = ndef[payload_start:payload_start + payload_len]
    if rec_type == b"U" and payload:
        prefix_map = {
            0x00: "",
            0x01: "http://www.",
            0x02: "https://www.",
            0x03: "http://",
            0x04: "https://",
            0x05: "tel:",
            0x06: "mailto:",
        }
        value = prefix_map.get(payload[0], "") + payload[1:].decode("utf-8", errors="replace")
        return {"type": "uri", "value": value, "raw_hex": ndef.hex(" ").upper()}
    if rec_type == b"T" and payload:
        status = payload[0]
        lang_len = status & 0x3F
        lang = payload[1:1 + lang_len].decode("ascii", errors="replace")
        text = payload[1 + lang_len:].decode("utf-8", errors="replace")
        return {"type": "text", "value": text, "language": lang, "raw_hex": ndef.hex(" ").upper()}
    return {"type": "unknown", "value": None, "raw_hex": ndef.hex(" ").upper()}


def read_raw_ndef_data(conn):
    raw = bytearray()
    for block in DATA_BLOCKS_1K_ALL_NFC:
        auth = authenticate_any(conn, block)
        if not auth["ok"]:
            if raw:
                break
            continue
        raw.extend(read_block(conn, block))
    return bytes(raw)


def read_decoded_ndef_from_conn(conn):
    raw = read_raw_ndef_data(conn)
    ndef = extract_ndef_from_raw(raw)
    return decode_ndef_message(ndef) if ndef else None


def format_mifare_classic_1k_as_ndef(conn):
    """
    Format a MIFARE Classic 1K card as MAD1/NDEF.

    Hotfix behavior:
    - Fresh/factory cards usually allow rewriting sector trailers.
    - Cards that were already formatted may authenticate and allow data writes,
      but refuse a second trailer rewrite with SW=63 00.
    - In that case, this function now skips the trailer rewrite and continues,
      because the sector is already in the protected NFC/NDEF state we need.

    This keeps "Format + Write" usable on cards that were formatted once already.
    """
    print("\nFormatting card as MIFARE Classic 1K NDEF/MAD1...")

    trailer_write_failures = []

    for sector in range(1, 16):
        trailer = sector_trailer_block(sector)
        auth = authenticate_any(
            conn,
            trailer,
            preferred=[
                ("DEFAULT_FF", KEY_DEFAULT_FF),
                ("NFC_FORUM", KEY_NFC_FORUM),
            ],
        )
        if not auth["ok"]:
            raise NFCError(f"Could not authenticate sector {sector} for formatting.")

        blocks = data_blocks_for_sector(sector)

        # Initialize payload/data blocks. These are safe data blocks, not trailers.
        write_block(conn, blocks[0], EMPTY_NDEF_FIRST_BLOCK if sector == 1 else EMPTY_BLOCK)
        write_block(conn, blocks[1], EMPTY_BLOCK)
        write_block(conn, blocks[2], EMPTY_BLOCK)

        # Trailer writes can fail on cards that have already been formatted once.
        # This is not fatal if the sector is already using NFC_FORUM access.
        try:
            write_block(conn, trailer, NFC_TRAILER, allow_trailer=True)
            print(f"Formatted NFC sector {sector:02d}")
        except NFCError as exc:
            trailer_write_failures.append((sector, str(exc)))
            print(
                f"Sector {sector:02d} data initialized, but trailer rewrite was blocked. "
                "Continuing; this usually means the sector was already NDEF-formatted."
            )

    # Format/update sector 0 MAD. On already-formatted cards, the MAD trailer
    # may also refuse rewriting, so data blocks are attempted and trailer failure
    # is handled as non-fatal.
    auth = authenticate_any(
        conn,
        3,
        preferred=[
            ("DEFAULT_FF", KEY_DEFAULT_FF),
            ("MAD_A", KEY_MAD_A),
            ("MAD_B", KEY_MAD_B),
        ],
    )
    if auth["ok"]:
        try:
            write_block(conn, 1, MAD_BLOCK_1)
            write_block(conn, 2, MAD_BLOCK_2)
            try:
                write_block(conn, 3, MAD_TRAILER, allow_trailer=True)
                print("Formatted MAD sector 0")
            except NFCError as exc:
                trailer_write_failures.append((0, str(exc)))
                print(
                    "MAD sector data written, but MAD trailer rewrite was blocked. "
                    "Continuing; this usually means the card was already formatted."
                )
        except NFCError as exc:
            # If the MAD blocks cannot be rewritten but the card already works
            # with NFC Forum sector keys, continue so the NDEF payload can be written.
            print(
                "MAD sector update was blocked. Continuing to payload write; "
                "this is expected on some already-formatted cards."
            )
            trailer_write_failures.append((0, str(exc)))
    else:
        print(
            "Could not authenticate MAD sector 0 with common MAD/default keys. "
            "Continuing to payload write; existing MAD may already be valid."
        )

    if trailer_write_failures:
        print("\nFormat note:")
        print("Some sector trailer rewrites were blocked. This is usually OK on a card")
        print("that was already formatted once. The payload write/verify step is the")
        print("real pass/fail check.")


def write_ndef_payload_to_nfc_sectors(conn, record_type, value):
    payload = make_mifare_classic_ndef_tlv_payload(record_type, value)
    blocks_needed = len(payload) // 16
    if blocks_needed > len(DATA_BLOCKS_1K_ALL_NFC):
        raise NFCError("Payload is too large for MIFARE Classic 1K NDEF data area.")
    print(f"\nNDEF/TLV payload size: {len(payload)} bytes")
    print(f"Blocks needed: {blocks_needed}")
    written = []
    for idx in range(blocks_needed):
        block = DATA_BLOCKS_1K_ALL_NFC[idx]
        chunk = payload[idx * 16:(idx + 1) * 16]
        auth = authenticate_any(conn, block, preferred=[("NFC_FORUM", KEY_NFC_FORUM), ("DEFAULT_FF", KEY_DEFAULT_FF)])
        if not auth["ok"]:
            raise NFCError(f"Could not authenticate block {block} for NDEF write.")
        print(f"Writing block {block:02d}: Key {auth['key_type']} / {auth['key_name']} -> {chunk.hex(' ').upper()}")
        write_block(conn, block, chunk)
        written.append(block)
    if blocks_needed < len(DATA_BLOCKS_1K_ALL_NFC):
        clear_block = DATA_BLOCKS_1K_ALL_NFC[blocks_needed]
        auth = authenticate_any(conn, clear_block, preferred=[("NFC_FORUM", KEY_NFC_FORUM), ("DEFAULT_FF", KEY_DEFAULT_FF)])
        if auth["ok"]:
            write_block(conn, clear_block, EMPTY_BLOCK)
    print("\nVerifying write...")
    readback = bytearray()
    for block in written:
        auth = authenticate_any(conn, block, preferred=[("NFC_FORUM", KEY_NFC_FORUM), ("DEFAULT_FF", KEY_DEFAULT_FF)])
        if not auth["ok"]:
            raise NFCError(f"Could not authenticate block {block} during verify.")
        readback.extend(read_block(conn, block))
    if bytes(readback[:len(payload)]) != payload:
        raise NFCError("Verification failed. Readback does not match payload.")
    print("SUCCESS: NDEF payload write verified.")


def inspect_card(reader):
    print_header("Scan / Inspect Card")
    print("Place the card on the ACR122U...")
    conn = connect_card(reader)
    try:
        uid = get_uid(conn)
        print(f"\nCard UID: {uid}")
        existing = read_decoded_ndef_from_conn(conn)
        if existing:
            print(f"NDEF detected: {existing.get('type')} -> {existing.get('value')}")
        else:
            print("NDEF detected: none/read failed")
        print("\nSector | Blocks      | Auth Result")
        print("-------+-------------+------------------------------------------")
        for sector in range(16):
            first = sector_first_block(sector)
            trailer = sector_trailer_block(sector)
            result = authenticate_any(conn, trailer)
            blocks = f"{first:02d}-{trailer:02d}"
            auth = f"OK using Key {result['key_type']} / {result['key_name']}" if result["ok"] else "FAILED with common keys"
            print(f"{sector:>6} | {blocks:<11} | {auth}")
    finally:
        try: conn.disconnect()
        except Exception: pass


def read_blocks(reader):
    print_header("Read MIFARE Classic 1K Data Blocks")
    print("Place the card on the ACR122U...")
    conn = connect_card(reader)
    try:
        uid = get_uid(conn)
        print(f"\nCard UID: {uid}\n")
        for block in DATA_BLOCKS_1K_ALL_NFC:
            auth = authenticate_any(conn, block)
            if not auth["ok"]:
                print(f"Block {block:02d}: auth failed")
                continue
            data = read_block(conn, block)
            ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in data)
            print(f"Block {block:02d}: {toHexString(data)}   |{ascii_part}|")
    finally:
        try: conn.disconnect()
        except Exception: pass


def read_and_decode_ndef(reader):
    print_header("Read / Decode NDEF From Card")
    print("Place the card on the ACR122U...")
    conn = connect_card(reader)
    try:
        uid = get_uid(conn)
        print(f"\nCard UID: {uid}")
        decoded = read_decoded_ndef_from_conn(conn)
        if not decoded:
            print("\nNo NDEF TLV found in readable data blocks.")
        else:
            print(f"\nNDEF type: {decoded.get('type')}")
            print(f"NDEF value: {decoded.get('value')}")
            if "language" in decoded:
                print(f"Language: {decoded.get('language')}")
            print(f"Raw NDEF: {decoded.get('raw_hex')}")
    finally:
        try: conn.disconnect()
        except Exception: pass


def choose_preset():
    presets = CONFIG.get("presets", [])
    if not presets:
        print("No presets found in config.json.")
        return None
    print_header("Business Card Presets")
    for idx, preset in enumerate(presets, 1):
        print(f"{idx}. {preset.get('name')} [{preset.get('type')}]")
        print(f"   {preset.get('value')}")
    while True:
        choice = input("\nChoose preset number, or blank to cancel: ").strip()
        if not choice:
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(presets):
            return presets[int(choice) - 1]
        print("Invalid selection.")


def write_flow(reader, preset=None, force_format=False):
    if preset:
        record_type = preset["type"]
        value = preset["value"]
    else:
        print_header("Custom NDEF Write")
        print("1. URL")
        print("2. Phone")
        print("3. Email")
        print("4. Text")
        mapping = {"1": "url", "2": "phone", "3": "email", "4": "text"}
        record_type = mapping.get(input("\nChoose type: ").strip())
        if not record_type:
            print("Canceled: invalid type.")
            return
        value = input("Enter value: ").strip()
        if not value:
            print("Canceled: empty value.")
            return

    _, normalized_value = normalize_record(record_type, value)
    print_header("Write Summary")
    print(f"Record type: {record_type}")
    print(f"Value:       {value}")
    print(f"NDEF value:  {normalized_value}")
    print("\nPlace the card on the ACR122U...")
    conn = connect_card(reader)
    uid = "unknown"
    try:
        uid = get_uid(conn)
        print(f"Card UID: {uid}")
        existing = read_decoded_ndef_from_conn(conn)
        if existing:
            print("\nExisting NDEF found:")
            print(f"Type:  {existing.get('type')}")
            print(f"Value: {existing.get('value')}")
            if CONFIG["settings"].get("require_confirmation_for_overwrite", True):
                if not yes_no("Overwrite existing NDEF?", default=False):
                    print("Canceled.")
                    log_write(uid, "write", record_type, value, "canceled", "existing NDEF not overwritten")
                    return
        else:
            print("\nExisting NDEF: none detected")
        action = "format_write" if force_format else "write"
        if force_format:
            if CONFIG["settings"].get("require_confirmation_for_format", True):
                print("\nThis will FORMAT the card as MIFARE Classic NDEF/MAD1 and write the payload.")
                if input("Type FORMAT to continue: ").strip() != "FORMAT":
                    print("Canceled.")
                    log_write(uid, action, record_type, value, "canceled", "format not confirmed")
                    return
            format_mifare_classic_1k_as_ndef(conn)
        write_ndef_payload_to_nfc_sectors(conn, record_type, value)
        decoded = read_decoded_ndef_from_conn(conn)
        if decoded:
            print("\nDecoded after write:")
            print(f"Type:  {decoded.get('type')}")
            print(f"Value: {decoded.get('value')}")
        log_write(uid, action, record_type, value, "success", f"decoded={decoded}")
        print("\nDone. Test the card with your phone.")
    except Exception as e:
        log_write(uid, "format_write" if force_format else "write", record_type, value, "failed", str(e))
        raise
    finally:
        try: conn.disconnect()
        except Exception: pass


def batch_write_flow(reader, preset=None, force_format=True):
    if not preset:
        preset = choose_preset()
    if not preset:
        print("Canceled.")
        return
    record_type = preset["type"]
    value = preset["value"]
    _, normalized_value = normalize_record(record_type, value)
    print_header("Batch Write Mode")
    print(f"Preset: {preset.get('name')}")
    print(f"Type:   {record_type}")
    print(f"Value:  {value}")
    print(f"NDEF:   {normalized_value}")
    print("\nThis writes multiple owned blank/business cards.")
    if force_format:
        if input("\nType BATCH to begin format+write batch mode: ").strip() != "BATCH":
            print("Canceled.")
            return
    success = 0
    failed = 0
    seen_uids = set()
    while True:
        cmd = input("\nPlace card on reader, then press Enter. Type q to quit: ").strip().lower()
        if cmd == "q":
            break
        conn = None
        uid = "unknown"
        try:
            conn = connect_card(reader)
            uid = get_uid(conn)
            if uid in seen_uids:
                print(f"UID {uid} was already written in this batch. Skipping duplicate.")
                continue
            print(f"\nCard UID: {uid}")
            existing = read_decoded_ndef_from_conn(conn)
            if existing:
                print(f"Existing NDEF: {existing.get('type')} -> {existing.get('value')}")
                if not yes_no("Overwrite this card?", default=False):
                    print("Skipped.")
                    log_write(uid, "batch_format_write", record_type, value, "skipped", "user skipped existing NDEF")
                    continue
            if force_format:
                format_mifare_classic_1k_as_ndef(conn)
            write_ndef_payload_to_nfc_sectors(conn, record_type, value)
            decoded = read_decoded_ndef_from_conn(conn)
            if decoded:
                print(f"Decoded: {decoded.get('type')} -> {decoded.get('value')}")
            success += 1
            seen_uids.add(uid)
            log_write(uid, "batch_format_write" if force_format else "batch_write", record_type, value, "success", f"decoded={decoded}")
            print(f"\nSuccess. Batch totals: success={success}, failed={failed}")
            print("Remove the card from the reader.")
            time.sleep(float(CONFIG["settings"].get("batch_delay_seconds_after_success", 1.0)))
        except NoCardException:
            print("No card detected.")
        except Exception as e:
            failed += 1
            print(f"Failed: {e}")
            log_write(uid, "batch_format_write" if force_format else "batch_write", record_type, value, "failed", str(e))
            print(f"Batch totals: success={success}, failed={failed}")
        finally:
            if conn:
                try: conn.disconnect()
                except Exception: pass
    print(f"\nBatch stopped. Final totals: success={success}, failed={failed}")


def show_config():
    print_header("Current Config")
    print(json.dumps(CONFIG, indent=2))


def edit_default_url():
    print_header("Edit Default URL")
    print(f"Current default URL: {CONFIG.get('default_url')}")
    new_url = input("New default URL, blank to cancel: ").strip()
    if not new_url:
        print("Canceled.")
        return
    CONFIG["default_url"] = new_url
    if CONFIG.get("presets"):
        CONFIG["presets"][0]["value"] = new_url
    save_config()
    print("Saved config.json")


def business_card_mode(reader):
    print_header("Business Card Mode")
    print(f"Business: {CONFIG.get('business_name')}")
    print(f"Owner:    {CONFIG.get('owner_name')}")
    print(f"Default:  {CONFIG.get('default_url')}")
    print("\n1. Format + write default business card")
    print("2. Write default business card without formatting")
    print("3. Choose another preset")
    print("4. Batch format + write default business card")
    print("5. Back")
    choice = input("\nChoose option: ").strip()
    default_preset = {"name": "Default Business Card", "type": "url", "value": CONFIG.get("default_url")}
    if choice == "1":
        write_flow(reader, default_preset, force_format=True)
    elif choice == "2":
        write_flow(reader, default_preset, force_format=False)
    elif choice == "3":
        preset = choose_preset()
        if preset:
            print("\n1. Format + write")
            print("2. Write without formatting")
            sub = input("Choose option: ").strip()
            write_flow(reader, preset, force_format=(sub != "2"))
    elif choice == "4":
        batch_write_flow(reader, default_preset, force_format=True)
    elif choice == "5":
        return
    else:
        print("Invalid option.")


def menu():
    print_header(APP_NAME)
    print("1. Business Card Mode")
    print("2. Custom Write")
    print("3. Batch Write Preset")
    print("4. Read / Decode NDEF")
    print("5. Scan / Inspect Card")
    print("6. Read Data Blocks")
    print("7. Show Config")
    print("8. Edit Default URL")
    print("9. List Readers")
    print("10. Exit")


def main():
    ensure_log_file()
    try:
        reader = pick_reader()
    except Exception as e:
        print(f"Startup error: {e}")
        return
    while True:
        menu()
        choice = input("\nChoose option: ").strip()
        try:
            if choice == "1":
                business_card_mode(reader)
            elif choice == "2":
                print("\n1. Format + write")
                print("2. Write without formatting")
                sub = input("Choose option: ").strip()
                write_flow(reader, preset=None, force_format=(sub != "2"))
            elif choice == "3":
                batch_write_flow(reader, preset=None, force_format=True)
            elif choice == "4":
                read_and_decode_ndef(reader)
            elif choice == "5":
                inspect_card(reader)
            elif choice == "6":
                read_blocks(reader)
            elif choice == "7":
                show_config()
            elif choice == "8":
                edit_default_url()
            elif choice == "9":
                print_header("Readers")
                for idx, r in enumerate(get_readers()):
                    print(f"[{idx}] {r}")
            elif choice == "10":
                print("Goodbye.")
                break
            else:
                print("Invalid option.")
        except NoCardException:
            print("No card detected. Place a card on the reader and try again.")
        except CardConnectionException as e:
            print(f"Card connection error: {e}")
        except NFCError as e:
            print(f"NFC error: {e}")
        except KeyboardInterrupt:
            print("\nCanceled.")
        except Exception as e:
            print(f"Unexpected error: {e}")
        pause()


if __name__ == "__main__":
    main()
