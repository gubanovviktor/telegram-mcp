import ipaddress
import struct

from telethon.sessions.string import CURRENT_VERSION, _STRUCT_PREFORMAT, StringSession


def _build_dummy_telegram_session_string() -> str:
    raw = struct.pack(
        _STRUCT_PREFORMAT.format(4),
        2,
        ipaddress.ip_address("149.154.167.51").packed,
        443,
        bytes(256),
    )
    return CURRENT_VERSION + StringSession.encode(raw)


VALID_DUMMY_TELEGRAM_SESSION_STRING = _build_dummy_telegram_session_string()
