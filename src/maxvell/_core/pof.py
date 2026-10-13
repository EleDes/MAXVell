# SPDX-License-Identifier: 0BSD
from __future__ import annotations
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from .hashutil import sha256_bytes
POF_MAGIC = b'POF\x00'
GLOBAL_HEADER_BYTES = 12
PACKET_HEADER_BYTES = 6
SECTION_HEADER_BYTES = 12
# General file-type reference, not a vendor specification of these binary fields.
POF_FORMAT_SOURCE_REFS = ['https://docs.altera.com/r/docs/683039/25.3.1/quartus-prime-pro-edition-user-guide/secondary-programming-files-convert-programming-files']
MANUFACTURER_PACKET_TAGS = {1: 'Creator_ID', 2: 'Device_Name', 3: 'Comment_Text', 4: 'Tag_Reserved', 5: 'Security_Bit', 6: 'Logical_Address_and_Data_16', 7: 'Electrical_Address_and_Data', 8: 'Terminator', 9: 'Symbol table', 10: 'Test Vectors', 12: 'Electrical_Address_and_Constant_data', 14: 'Number of programmable elements', 17: 'Logical_Address_and_Data_32'}
PACKET_ROLES = {1: 'creator', 2: 'device', 3: 'comment_or_option_text', 5: 'security_bit', 17: 'cfm_section', 24: 'ufm_section', 8: 'terminator_crc'}

@dataclass(frozen=True)
class Packet:
    packet_id: int
    offset: int
    payload_offset: int
    length: int
    sha256: str
    role: str
    manufacturer_name: str | None
    manufacturer_source_refs: tuple[str, ...]
    payload: bytes

    def public_dict(self) -> dict[str, object]:
        data = asdict(self)
        data.pop('payload')
        data['packet_id_hex'] = f'0x{self.packet_id:04X}'
        return data

@dataclass(frozen=True)
class Section:
    packet_id: int
    bit_length: int
    header_hex: str
    payload_offset: int
    payload_length: int
    payload_sha256: str

@dataclass(frozen=True)
class TerminatorCrc:
    packet_id: int
    stored_crc: int
    calculated_crc: int | None
    crc_ok: bool | None
    ignored: bool
    algorithm: str
    source_refs: tuple[str, ...]

@dataclass(frozen=True)
class PofFile:
    path: Path
    header: bytes
    packet_count: int
    packets: tuple[Packet, ...]
    data: bytes

    def packet(self, packet_id: int) -> Packet:
        matches = [packet for packet in self.packets if packet.packet_id == packet_id]
        if len(matches) != 1:
            raise ValueError(f'Expected exactly one packet 0x{packet_id:04X}, got {len(matches)}')
        return matches[0]

    def text_packet(self, packet_id: int) -> str | None:
        try:
            payload = self.packet(packet_id).payload
        except ValueError:
            return None
        return payload.rstrip(b'\x00').decode('latin1', errors='replace')

    def section(self, packet_id: int) -> Section:
        packet = self.packet(packet_id)
        if len(packet.payload) < SECTION_HEADER_BYTES:
            raise ValueError(f'Packet 0x{packet_id:04X} has no full section header')
        bit_length = struct.unpack_from('<I', packet.payload, 6)[0]
        payload = packet.payload[SECTION_HEADER_BYTES:]
        return Section(packet_id=packet_id, bit_length=bit_length, header_hex=packet.payload[:SECTION_HEADER_BYTES].hex(), payload_offset=packet.payload_offset + SECTION_HEADER_BYTES, payload_length=len(payload), payload_sha256=sha256_bytes(payload))

    def section_payload(self, packet_id: int) -> bytes:
        packet = self.packet(packet_id)
        if len(packet.payload) < SECTION_HEADER_BYTES:
            raise ValueError(f'Packet 0x{packet_id:04X} has no full section header')
        return packet.payload[SECTION_HEADER_BYTES:]

    def terminator_crc(self) -> TerminatorCrc | None:
        try:
            packet = self.packet(8)
        except ValueError:
            return None
        if len(packet.payload) != 2:
            raise ValueError(f'Terminator packet has {len(packet.payload)} CRC bytes, expected 2')
        stored_crc = struct.unpack('<H', packet.payload)[0]
        ignored = stored_crc == 0
        calculated_crc = None if ignored else crc16_x25(self.data[:packet.payload_offset])
        return TerminatorCrc(packet_id=8, stored_crc=stored_crc, calculated_crc=calculated_crc, crc_ok=None if ignored else stored_crc == calculated_crc, ignored=ignored, algorithm='CRC-16/X-25', source_refs=tuple(POF_FORMAT_SOURCE_REFS))

def crc16_x25(data: bytes) -> int:
    crc = 65535
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = crc >> 1 ^ 33800
            else:
                crc >>= 1
            crc &= 65535
    return crc ^ 65535

def load_pof(path: Path, *, data: bytes | None=None) -> PofFile:
    """Parse a POF path, optionally from caller-snapshotted bytes.

    Supplying ``data`` lets checksum-bound consumers hash and parse the exact
    same byte snapshot without reopening a living input path.
    """
    if data is None:
        data = path.read_bytes()
    if len(data) < GLOBAL_HEADER_BYTES or data[:4] != POF_MAGIC:
        raise ValueError('Input is not a Quartus POF file')
    packet_count = struct.unpack_from('<I', data, 8)[0]
    offset = GLOBAL_HEADER_BYTES
    packets: list[Packet] = []
    for index in range(packet_count):
        if offset + PACKET_HEADER_BYTES > len(data):
            raise ValueError(f'Truncated packet header at index {index}')
        packet_id, payload_length = struct.unpack_from('<HI', data, offset)
        payload_offset = offset + PACKET_HEADER_BYTES
        payload_end = payload_offset + payload_length
        if payload_end > len(data):
            raise ValueError(f'Packet 0x{packet_id:04X} overruns file')
        payload = data[payload_offset:payload_end]
        packets.append(Packet(packet_id=packet_id, offset=offset, payload_offset=payload_offset, length=payload_length, sha256=sha256_bytes(payload), role=PACKET_ROLES.get(packet_id, 'unknown'), manufacturer_name=MANUFACTURER_PACKET_TAGS.get(packet_id), manufacturer_source_refs=tuple(POF_FORMAT_SOURCE_REFS) if packet_id in MANUFACTURER_PACKET_TAGS else (), payload=payload))
        offset = payload_end
    if offset != len(data):
        raise ValueError(f'Unexpected trailing POF data: {len(data) - offset} bytes')
    return PofFile(path=path, header=data[:GLOBAL_HEADER_BYTES], packet_count=packet_count, packets=tuple(packets), data=data)
