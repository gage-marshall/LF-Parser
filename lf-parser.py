#!/usr/bin/env python3
"""
lf-parser.py

Not affiliated with or endorsed by Fisnar Inc. Use at your own risk.

Decode/Encode Fisnar ".LF" motion-control files with editable plaintext and byte-perfect round-trip.

Usage:
  Decode an LF → text:
    python lf-parser.py -d input.lf -o output.txt

  Encode text → LF:
    python lf-parser.py -e input.txt -o output.lf

When decoding, each 16-byte record is printed as:
    XX CommandName [param1 param2 ...]    # raw: <32 hex>

"""

import sys, struct, argparse

# COLUMN where "# raw:" comments begin
RAW_COLUMN = 60

# Command ID → human‐readable string
CMD_ID_TO_NAME = {
    0:   "Empty",
    1:   "Line Speed",
    2:   "Line Passing",
    3:   "Arc Point",
    4:   "Line Start",
    5:   "Dispense Dot",
    6:   "Output",
    7:   "Input",
    9:   "Wait Point",
    11:  "End Program",
    12:  "Line End",
    13:  "Step & Repeat X",
    18:  "Stop Point",
    19:  "Empty",  # distinct from cmd_id=0
    20:  "Point Dispense Setup",
    21:  "Line Dispense Setup",
    22:  "Z Clearance",
    23:  "Dispense End Setup",
    27:  "Goto Address",
    28:  "Brush Area",
    29:  "Call Subroutine",
    30:  "Call Program",
    31:  "Dummy Point CP",
    32:  "Step & Repeat Y",
    33:  "Dispense ON/OFF",
    35:  "Home Point",
    36:  "Loop Address",
    37:  "Circle",
    38:  "Retract Setup",
    39:  "Initialize",
    40:  "Label",
    43:  "Acceleration",
    51:  "Blend Point",
    53:  "Circle Dispense Setup",
    54:  "Dispense Outport",
    55:  "Dummy Point PTP",
    57:  "Cubical Layer",
    66:  "Height Sensor Point",
    67:  "Pause Point",
    68:  "Output Toggle",
    69:  "Wait Input",
    70:  "Check Block",
    71:  "Acc Time",
    72:  "Dummy Start",
    73:  "Dummy Passing",
    74:  "Dummy Arc",
    75:  "Dummy End",
    76:  "Fixed Point",
    127: "Padding",
}

# SysMem field (offset, dtype, optional transform function)
# dtype is one of: "int8","int16","int32","float32","str[N]" or "bitX"
sysmem_field_map = {
    "ProgramSize":        (207,  "int32",    lambda v: v + 1),
    "XYMoveSpeed":        (12,   "float32"),
    "ZMoveSpeed":         (44,   "float32"),
    "DebugSpeed":         (105,  "float32"),
    "TipHomeX":           (85,   "float32"),
    "TipHomeY":           (89,   "float32"),
    "TipHomeZ":           (93,   "float32"),
    "TipAdjustX":         (109,  "float32"),
    "TipAdjustY":         (113,  "float32"),
    "TipAdjustZ":         (117,  "float32"),
    "SoftOrgX":           (267,  "float32"),
    "SoftOrgY":           (271,  "float32"),
    "SoftOrgZ":           (275,  "float32"),
    "AutoPurgeWaitTime":  (178,  "float32"),
    "AutoPurgeDispenseTime": (182,"float32"),
    "ZLimit":             (79,   "float32"),
    "PreDispenseWait":    (263,  "float32"),
    "RunCounter":         (70,   "int16"),
    "QuickStep":          (177,  "int8",     lambda v: 1 if v else 0),
    "RunningHomeFirst":   (397,  "int8",     lambda v: 0 if v else 1),
    "EmergencyMode":      (190,  "int8",     lambda v: 1 if v == "Maintaining" else 0),
    "ProgramLabel":       (52,   "str[15]"),
    "MagicSignature_398": (398,  "int16"),
}
# Pack bits O1–O8 at offset 83 (2 bytes)
for i in range(8):
    sysmem_field_map[f"O{i+1}"] = (83, f"bit{i}")


def decode_command_records(data: bytes, lines: list):

    body = data[:-400]
    sysmem = data[-400:]
    n_recs = len(body) // 16

    lines.append(f"# {n_recs} records")
    offset = 0

    for _ in range(n_recs):
        rec = body[offset : offset + 16]
        offset += 16

        # Padding check: first 15 bytes = 0x00, last byte = 0xFF
        if rec[:15] == b"\x00" * 15 and rec[15] == 0xFF:
            left_part = "FF Padding"
            raw_hex = rec.hex().upper()
            spaces_needed = max(1, RAW_COLUMN - len(left_part) - 1)
            lines.append(left_part + (" " * spaces_needed) + f"# raw: {raw_hex}")
            continue

        byte15 = rec[15]
        cmd_id = byte15 & 0x7F
        name = CMD_ID_TO_NAME.get(cmd_id, f"UNKNOWN_{cmd_id}")

        # Unpack parameters
        params = []
        def rf(o): return struct.unpack_from("<f", rec, o)[0]
        def ri(o): return struct.unpack_from("<h", rec, o)[0]

        if cmd_id == 54:
            params.append(ri(12))
        elif cmd_id == 1:
            params.append(rf(0))
            params.append(rec[14])
        elif cmd_id in (9, 71):
            params.append(rf(0))
        elif cmd_id in (27, 30, 40):
            params.append(ri(12))
        elif cmd_id in (33, 76):
            params.append(rec[14])
        elif cmd_id == 22:
            params.append(rf(0))
            params.append(rec[14])
        elif cmd_id in (6, 53):
            params.append(rf(0))
            params.append(rf(4))
        elif cmd_id == 68:
            params.append(rf(0))
            params.append(rf(4))
            params.append(rf(8))
        elif cmd_id == 36:
            params.append(ri(12))
            params.append(rf(0))
        elif cmd_id == 28:
            params.append(rf(0))
            params.append(rf(4))
            # displayed as byte[14] + 1
            params.append(rec[14] + 1)
            params.append(ri(12))
        elif cmd_id == 70:
            params.append(ri(8))
            params.append(ri(10))
        elif cmd_id in (7, 43):
            params.append(ri(8))
            params.append(ri(10))
            params.append(ri(12))
        elif cmd_id == 69:
            params.append(ri(8))
            params.append(ri(10))
        elif cmd_id == 23:
            params.append(rf(0))
            params.append(rf(4))
            params.append(rf(8))
        elif cmd_id in (2, 3, 4, 5, 12, 18, 31, 55, 67, 72, 73, 74, 75):
            params.append(rf(0))
            params.append(rf(4))
            params.append(rf(8))
        elif cmd_id == 66:
            params.append(rf(0))
            params.append(rf(4))
            params.append(rf(8))
            params.append(ri(12) / 100.0)
        elif cmd_id == 21:
            params.append(rf(0))
            params.append(ri(10) / 1000.0)
            params.append(rf(4))
            params.append(ri(12) / 1000.0)
            params.append(ri(8) / 1000.0)
        elif cmd_id == 37:
            params.append(rf(0))
            params.append(rf(4))
            params.append(rf(8))
            params.append(ri(12) / 100.0)
        elif cmd_id in (29, 38):
            params.append(rf(0))
            params.append(rf(4))
            params.append(rf(8))
            params.append(ri(12))
        elif cmd_id in (13, 32):
            params.append(ri(0) / 100.0)
            params.append(ri(2) / 100.0)
            params.append(ri(10))
            params.append(ri(12))
            params.append(rec[14])
            params.append(ri(8))
        # else: no parameters

        if params:
            outp = []
            for p in params:
                if isinstance(p, float):
                    if abs(p - round(p)) < 1e-6:
                        outp.append(str(int(round(p)))
)
                    else:
                        outp.append(f"{p:.6g}")
                else:
                    outp.append(str(p))
            left_part = f"{byte15:02X} {name} {' '.join(outp)}"
        else:
            left_part = f"{byte15:02X} {name}"

        raw_hex = rec.hex().upper()
        spaces_needed = max(1, RAW_COLUMN - len(left_part) - 1)
        lines.append(left_part + (" " * spaces_needed) + f"# raw: {raw_hex}")

    return sysmem


def decode_sysmem_pretty(sysmem: bytes, lines: list, raw_column=RAW_COLUMN):
    """
    Print each mapped SysMem field as its own entry (Field: value    # raw: <hex>).
    Then print a final "unmapped raw" 400-byte block so encoding can preserve those bytes exactly.
    """
    def get_int(offset, size):
        if size == 1:
            return struct.unpack_from("<b", sysmem, offset)[0]
        if size == 2:
            return struct.unpack_from("<h", sysmem, offset)[0]
        if size == 4:
            return struct.unpack_from("<i", sysmem, offset)[0]
        raise ValueError("Unsupported int size")

    def get_float(offset):
        return struct.unpack_from("<f", sysmem, offset)[0]

    def get_string(offset, length):
        raw = sysmem[offset:offset + length]
        if b"\x00" in raw:
            raw = raw.split(b"\x00", 1)[0]
        try:
            return raw.decode("ascii", errors="ignore")
        except:
            return "<invalid>"

    def get_raw(offset, size):
        return sysmem[offset : offset + size].hex().upper()

    # Emit header for decoded fields
    lines.append("===== SysMem (decoded fields) =====")

    # Track which offsets have been covered by mapped fields
    covered = set()

    for field, info in sysmem_field_map.items():
        offset, dtype = info[0], info[1]
        raw = ""

        if dtype.startswith("bit"):
            # skip bits here; we'll emit them after collecting all O1–O8
            continue

        if dtype == "int8":
            val = get_int(offset, 1)
            raw = get_raw(offset, 1)
            covered.update(range(offset, offset+1))

        elif dtype == "int16":
            val = get_int(offset, 2)
            raw = get_raw(offset, 2)
            covered.update(range(offset, offset+2))

        elif dtype == "int32":
            val = get_int(offset, 4)
            raw = get_raw(offset, 4)
            covered.update(range(offset, offset+4))

        elif dtype == "float32":
            val = get_float(offset)
            raw = get_raw(offset, 4)
            covered.update(range(offset, offset+4))

        elif dtype.startswith("str["):
            length = int(dtype[4:-1])
            val = get_string(offset, length)
            raw = get_raw(offset, length)
            covered.update(range(offset, offset+length))

        else:
            # unknown dtype (should not happen (famous last words))
            continue

        # Reverse transforms
        if len(info) > 2:
            if field == "ProgramSize":
                val -= 1
            elif field == "QuickStep":
                val = (val != 0)
            elif field == "RunningHomeFirst":
                val = (val == 0)
            elif field == "EmergencyMode":
                val = "Maintaining" if val else "Initial"

        text = f"{field}: {val}"
        pad = max(1, RAW_COLUMN - len(text) - 1)
        lines.append(text + (" " * pad) + f"# raw: {raw}")

    # Emit O1–O8 bits (packed in 2-byte int at offset 83)
    oflags = struct.unpack_from("<H", sysmem, 83)[0]
    covered.update([83, 84])  # those two bytes used by all O1–O8

    for i in range(8):
        bit = (oflags >> i) & 1
        text = f"O{i+1}: {bool(bit)}"
        pad = max(1, RAW_COLUMN - len(text) - 1)
        lines.append(text + (" " * pad) + f"# raw: {(oflags & 0xFFFF):04X}")

    # Emit a final raw block for any offsets not covered above,
    # so that encoding can preserve them exactly.
    lines.append("===== SysMem (unmapped raw) =====")
    # Print 20 bytes per line, from byte 0..399
    for i in range(0, 400, 20):
        slab = sysmem[i : i + 20]
        hex_vals = " ".join(f"{b:02X}" for b in slab)
        lines.append(hex_vals)


def encode_sysmem_from_fields(lines: list, start_idx: int):

    sysmem = bytearray(400)
    bitfields = {}

    for idx in range(start_idx + 1, len(lines)):
        line = lines[idx].strip()
        if not line or line.startswith("====="):
            break
        if ":" not in line:
            continue

        field, value = map(str.strip, line.split(":", 1))

        # If #raw comment is in place, skip and just copy from unmapped block
        if "# raw:" in line:
            continue

        # Otherwise, re-encode
        if field not in sysmem_field_map:
            continue

        offset, dtype = sysmem_field_map[field][:2]
        transform = (
            sysmem_field_map[field][2]
            if len(sysmem_field_map[field]) > 2
            else (lambda v: v)
        )

        try:
            if dtype.startswith("bit"):
                bit = int(dtype[3:])
                val = value.lower() in ("1", "true", "yes")
                bitfields.setdefault(offset, 0)
                if val:
                    bitfields[offset] |= (1 << bit)

            elif dtype == "int8":
                sysmem[offset] = transform(value) & 0xFF

            elif dtype == "int16":
                struct.pack_into("<h", sysmem, offset, transform(int(value)))

            elif dtype == "int32":
                struct.pack_into("<i", sysmem, offset, transform(int(value)))

            elif dtype == "float32":
                struct.pack_into("<f", sysmem, offset, float(value))

            elif dtype.startswith("str["):
                length = int(dtype[4:-1])
                encoded = value.encode("ascii", errors="ignore")[:length]
                sysmem[offset : offset + length] = encoded + b"\x00" * (length - len(encoded))

        except Exception as e:
            raise ValueError(f"Error encoding field '{field}': {e}")

    # Write collected bitfields (O1..O8)
    for offset, bits in bitfields.items():
        struct.pack_into("<H", sysmem, offset, bits)

    return bytes(sysmem)


def _pack_record_from_text(text_part: str, original_line: str) -> bytes:
    """
    Given a text line without "# raw:", of the form:
      "<HEX15> <CommandName> [param1 param2 ...]"
    parse tokens and pack into a 16-byte record.
    """
    tokens = text_part.split()
    if len(tokens) < 2:
        raise ValueError(f"Invalid record line (too few tokens): '{original_line}'")

    hex15 = tokens[0]
    if len(hex15) != 2:
        raise ValueError(
            f"Expected two-digit hex for byte15, got '{hex15}' in line: '{original_line}'"
        )
    try:
        byte15 = int(hex15, 16)
    except ValueError:
        raise ValueError(f"Invalid hex '{hex15}' in line: '{original_line}'")

    # Padding line if byte15 == 0xFF
    if byte15 == 0xFF:
        return b"\x00" * 15 + b"\xFF"

    # Otherwise, build 16-byte buffer and fill in fields
    bcar = bytearray(16)
    bcar[15] = byte15

    # Distinguish command name tokens vs parameter tokens
    name_tokens = []
    param_tokens = []
    seen_param = False
    for tok in tokens[1:]:
        if not seen_param:
            try:
                _ = float(tok)
                seen_param = True
                param_tokens.append(tok)
            except ValueError:
                name_tokens.append(tok)
        else:
            param_tokens.append(tok)

    # Convert param_tokens into numeric list
    val_list = []
    for p in param_tokens:
        if "." in p or "e" in p or "E" in p:
            try:
                val_list.append(float(p))
            except ValueError:
                raise ValueError(f"Cannot parse '{p}' as float in line: '{original_line}'")
        else:
            try:
                val_list.append(int(p))
            except ValueError:
                raise ValueError(f"Cannot parse '{p}' as int in line: '{original_line}'")

    cmd_id = byte15 & 0x7F
    vi = 0  # index into val_list

    # Now pack fields according to cmd_id
    if cmd_id == 54:
        p = int(val_list[vi]); vi += 1
        struct.pack_into("<h", bcar, 12, p)

    elif cmd_id == 1:
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 0, f0)
        p1 = int(val_list[vi]); vi += 1
        bcar[14] = p1

    elif cmd_id in (9, 71):
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 0, f0)

    elif cmd_id in (27, 30, 40):
        p = int(val_list[vi]); vi += 1
        struct.pack_into("<h", bcar, 12, p)

    elif cmd_id in (33, 76):
        p = int(val_list[vi]); vi += 1
        bcar[14] = p

    elif cmd_id == 22:
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 0, f0)
        p1 = int(val_list[vi]); vi += 1
        bcar[14] = p1

    elif cmd_id in (6, 53):
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 0, f0)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 4, f1)

    elif cmd_id == 68:
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 0, f0)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 4, f1)
        f2 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 8, f2)

    elif cmd_id == 36:
        p = int(val_list[vi]); vi += 1
        struct.pack_into("<h", bcar, 12, p)
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 0, f0)

    elif cmd_id == 28:
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 0, f0)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 4, f1)
        p2 = int(val_list[vi]); vi += 1
        bcar[14] = p2 - 1
        p3 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", bcar, 12, p3)

    elif cmd_id == 70:
        p = int(val_list[vi]); vi += 1
        struct.pack_into("<h", bcar, 8, p)
        p2 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", bcar, 10, p2)

    elif cmd_id in (7, 43):
        p = int(val_list[vi]); vi += 1
        struct.pack_into("<h", bcar, 8, p)
        p2 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", bcar, 10, p2)
        p3 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", bcar, 12, p3)

    elif cmd_id == 69:
        p = int(val_list[vi]); vi += 1
        struct.pack_into("<h", bcar, 8, p)
        p2 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", bcar, 10, p2)

    elif cmd_id == 23:
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 0, f0)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 4, f1)
        f2 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 8, f2)

    elif cmd_id in (2, 3, 4, 5, 12, 18, 31, 55, 67, 72, 73, 74, 75):
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 0, f0)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 4, f1)
        f2 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 8, f2)

    elif cmd_id == 66:
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 0, f0)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 4, f1)
        f2 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 8, f2)
        p3 = int(round(val_list[vi] * 100)); vi += 1
        struct.pack_into("<h", bcar, 12, p3)

    elif cmd_id == 21:
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 0, f0)
        p2 = int(round(val_list[vi] * 1000)); vi += 1
        struct.pack_into("<h", bcar, 10, p2)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 4, f1)
        p4 = int(round(val_list[vi] * 1000)); vi += 1
        struct.pack_into("<h", bcar, 12, p4)
        p5 = int(round(val_list[vi] * 1000)); vi += 1
        struct.pack_into("<h", bcar, 8, p5)

    elif cmd_id == 37:
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 0, f0)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 4, f1)
        f2 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 8, f2)
        p4 = int(round(val_list[vi] * 100)); vi += 1
        struct.pack_into("<h", bcar, 12, p4)

    elif cmd_id in (29, 38):
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 0, f0)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 4, f1)
        f2 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", bcar, 8, f2)
        p3 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", bcar, 12, p3)

    elif cmd_id in (13, 32):
        p1 = int(round(val_list[vi] * 100)); vi += 1
        struct.pack_into("<h", bcar, 0, p1)
        p2 = int(round(val_list[vi] * 100)); vi += 1
        struct.pack_into("<h", bcar, 2, p2)
        p3 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", bcar, 10, p3)
        p4 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", bcar, 12, p4)
        p5 = int(val_list[vi]); vi += 1
        bcar[14] = p5
        p6 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", bcar, 8, p6)

    return bytes(bcar)


def encode_records_from_text(lines: list):
 
    recs = bytearray()
    idx = 0

    while idx < len(lines):
        ln = lines[idx].rstrip("\n")
        strip_ln = ln.strip()

        # Skip blanks or comments
        if not strip_ln or strip_ln.startswith("#"):
            idx += 1
            continue

        # Stop at SysMem section
        if strip_ln.startswith("===== SysMem (decoded fields)"):
            break

        # If "# raw:" is present, copy exactly 16 bytes
        if "# raw:" in ln:
            _, raw_part = ln.split("# raw:", 1)
            raw_hex = raw_part.strip().replace(" ", "")
            if len(raw_hex) != 32:
                raise ValueError(f"Expected 32 hex chars after '# raw:', got '{raw_hex}'")
            rec = bytes.fromhex(raw_hex)
            if len(rec) != 16:
                raise ValueError(f"Raw hex did not decode to 16 bytes: '{ln}'")
            recs.extend(rec)
        else:
            # No raw, re-pack from text
            rec = _pack_record_from_text(ln, ln)
            recs.extend(rec)

        idx += 1

    return recs, idx


def parse_unmapped_raw(lines: list, start_idx: int):
    """
    Starting below '===== SysMem (unmapped raw) =====', read next 400 raw bytes (20 per line).
    Returns (bytes_of_400, next_index).
    """
    idx = start_idx + 1
    hex_bytes = []

    while idx < len(lines):
        ln = lines[idx].strip()
        if not ln:
            idx += 1
            continue
        if ln.startswith("====="):
            break
        parts = ln.split()
        for h in parts:
            if len(hex_bytes) < 400:
                hex_bytes.append(int(h, 16))
        idx += 1
        if len(hex_bytes) >= 400:
            break

    if len(hex_bytes) < 400:
        raise ValueError("Could not parse 400 bytes of unmapped SysMem.")
    return bytes(hex_bytes[:400]), idx


def encode_file(infile: str, outfile: str):
  
    all_lines = open(infile, "r", encoding="utf-8").read().splitlines()

    # Re‐pack all 16‐byte records
    recs, idx = encode_records_from_text(all_lines)

    # Identify which fields lost “# raw:”
    to_reencode = set()
    header_unmapped = "===== SysMem (unmapped raw) ====="
    i = idx
    while i < len(all_lines):
        line = all_lines[i].strip()
        if line.startswith(header_unmapped):
            break
        if ":" in line and "# raw:" not in line:
            field_name = line.split(":", 1)[0].strip()
            if field_name in sysmem_field_map:
                to_reencode.add(field_name)
        i += 1

    # Re‐encode only those fields into zeroed 400‐byte “mapped_buffer”
    mapped_buffer = encode_sysmem_from_fields(all_lines, idx)

    # Parse the full 400 bytes of “unmapped raw”
    try:
        idx_unmapped = all_lines.index(header_unmapped)
    except ValueError:
        raise ValueError("Could not find '===== SysMem (unmapped raw) =====' in the decoded file.")
    unmapped_base, _ = parse_unmapped_raw(all_lines, idx_unmapped)

    # Overlay only those offsets whose field lost “# raw:”
    final_sysmem = bytearray(unmapped_base)
    for field in to_reencode:
        offset, dtype = sysmem_field_map[field][:2]
        if dtype.startswith("bit"):
            final_sysmem[offset : offset + 2] = mapped_buffer[offset : offset + 2]
        elif dtype == "int8":
            final_sysmem[offset] = mapped_buffer[offset]
        elif dtype == "int16":
            final_sysmem[offset : offset + 2] = mapped_buffer[offset : offset + 2]
        elif dtype in ("int32", "float32"):
            final_sysmem[offset : offset + 4] = mapped_buffer[offset : offset + 4]
        elif dtype.startswith("str["):
            length = int(dtype[4:-1])
            final_sysmem[offset : offset + length] = mapped_buffer[offset : offset + length]
        # else: unknown dtype

    # Write recs + the correctly overlaid 400‐byte SysMem
    with open(outfile, "wb") as fout:
        fout.write(recs)
        fout.write(bytes(final_sysmem))

    print(f"Encoded {infile} → {outfile}")


def decode_file(infile: str, outfile: str):
    data = open(infile, "rb").read()
    if len(data) < 500:
        print("Error: file too small (<500 bytes).")
        sys.exit(1)

    lines = []
    sysmem = decode_command_records(data, lines)
    decode_sysmem_pretty(sysmem, lines)

    with open(outfile, "w", encoding="utf-8") as fout:
        fout.write("\n".join(lines))

    print(f"Decoded {infile} → {outfile}")


def main():
    parser = argparse.ArgumentParser(description="Decode/Encode Fisnar LF motion-control files")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-d", "--decode", action="store_true", help="Decode .LF to text")
    group.add_argument("-e", "--encode", action="store_true", help="Encode text to .LF")
    parser.add_argument("input", help="Input filename")
    parser.add_argument("-o", "--output", required=True, help="Output filename")
    args = parser.parse_args()

    if args.decode:
        decode_file(args.input, args.output)
    else:
        encode_file(args.input, args.output)


if __name__ == "__main__":
    main()
