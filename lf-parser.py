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
    XX CommandName [param1 param2 ...]    # raw: <32 hex chars>

You may remove the #raw comment from a line, edit the plaintext parameters and re-encode them to a valid .LF program.

"""
import sys, os, struct, argparse

# 1) Command‐ID → human‐readable name
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


def decode_command_records(data, lines):
    """
    Decode the first (len(data)-400) bytes as 16-byte records.
    Each line is formatted as:
      XX CommandName [param1 param2 ...] <padding spaces> # raw: <32 hex chars>

    All "# raw:" comments will begin at the same fixed column (RAW_COLUMN),
    making them line up in a neat vertical block.
    """
    body   = data[:-400]
    sysmem = data[-400:]
    n_recs = len(body) // 16

    # Choose which column (1‐indexed) you want "# raw:" to start at. 
    # For example, RAW_COLUMN = 60 means that the first character of "# raw:" is at position 60.
    RAW_COLUMN = 60

    lines.append(f"# {n_recs} records")

    offset = 0
    for _ in range(n_recs):
        rec = body[offset : offset + 16]
        offset += 16

        # Fisnar's programs are usually padded to length. Padding line check: first 15 bytes = 0x00, last byte = 0xFF
        if rec[:15] == b"\x00" * 15 and rec[15] == 0xFF:
            left_part = "FF Padding"
            raw_hex = rec.hex().upper()
            # Compute how many spaces to add so that "# raw:" is at RAW_COLUMN
            spaces_needed = max(1, RAW_COLUMN - len(left_part) - 1)
            lines.append(left_part + (" " * spaces_needed) + f"# raw: {raw_hex}")
            continue

        # Normal record: decode byte15, name, parameters
        byte15 = rec[15]
        cmd_id = byte15 & 0x7F
        name   = CMD_ID_TO_NAME.get(cmd_id, f"UNKNOWN_{cmd_id}")

        # Unpack parameters:
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
            params.append(ri(8)  / 1000.0)
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
            params.append(ri(0)  / 100.0)
            params.append(ri(2)  / 100.0)
            params.append(ri(10))
            params.append(ri(12))
            params.append(rec[14])
            params.append(ri(8))
        # else: no parameters

        # Build "left_part" (human readable data before "# raw:")
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
        # Compute how many spaces to add so that "# raw:" is at RAW_COLUMN
        spaces_needed = max(1, RAW_COLUMN - len(left_part) - 1)
        lines.append(left_part + (" " * spaces_needed) + f"# raw: {raw_hex}")

    return sysmem



def decode_sysmem(sysmem, lines):

    # Append sysmem headers:
    lines.append("===== SysMem (400 bytes) as raw hex =====")
    hex_list = [f"{b:02X}" for b in sysmem]
    for i in range(0, 400, 20):
        lines.append(" ".join(hex_list[i:i+20]))

    lines.append("===== SysMem (decoded fields) =====")

    def get_int(offset, size):
        if size == 1: return struct.unpack_from("<b", sysmem, offset)[0]
        if size == 2: return struct.unpack_from("<h", sysmem, offset)[0]
        if size == 4: return struct.unpack_from("<i", sysmem, offset)[0]
        raise ValueError("Unsupported int size")

    def get_float(offset):
        return struct.unpack_from("<f", sysmem, offset)[0]

    def get_string(offset, length):
        raw = sysmem[offset:offset+length]
        if b"\x00" in raw: raw = raw.split(b"\x00", 1)[0]
        try: return raw.decode("ascii", errors="ignore")
        except: return "<invalid>"

    prog_raw = get_int(207, 4)
    lines.append(f"ProgramSize: {prog_raw - 1}")
    lines.append(f"XYMoveSpeed: {get_float(12)}")
    lines.append(f"ZMoveSpeed: {get_float(44)}")
    lines.append(f"DebugSpeed: {get_float(105)}")
    lines.append(f"TipHomeX: {get_float(85)}")
    lines.append(f"TipHomeY: {get_float(89)}")
    lines.append(f"TipHomeZ: {get_float(93)}")
    lines.append(f"TipAdjustX: {get_float(109)}")
    lines.append(f"TipAdjustY: {get_float(113)}")
    lines.append(f"TipAdjustZ: {get_float(117)}")
    lines.append(f"SoftOrgX: {get_float(267)}")
    lines.append(f"SoftOrgY: {get_float(271)}")
    lines.append(f"SoftOrgZ: {get_float(275)}")
    lines.append(f"AutoPurgeWaitTime: {get_float(178)}")
    lines.append(f"AutoPurgeDispenseTime: {get_float(182)}")
    lines.append(f"ZLimit: {get_float(79)}")
    lines.append(f"PreDispenseWait: {get_float(263)}")
    run_cn = get_int(70, 2); lines.append(f"RunCounter: {run_cn}")
    quick = get_int(177, 1); lines.append(f"QuickStep: {bool(quick != 0)}")
    rh = get_int(397, 1); lines.append(f"RunningHomeFirst: {bool(rh == 0)}")
    emg = get_int(190, 1)
    lines.append(f"EmergencyMode: {'Maintaining' if emg != 0 else 'Initial'}")
    prog_label = get_string(52, 15); lines.append(f"ProgramLabel: {prog_label}")
    oflags = get_int(83, 2)
    for bit in range(8):
        lines.append(f"O{bit+1}: {bool(oflags & (1 << bit))}")
    magic398 = get_int(398, 2); lines.append(f"MagicSignature_398: {magic398}")


def encode_records_from_text(lines):
    """
    Read lines up to raw sysmem header
    For each record line:
      - If “# raw: <32hex>” is present → take those 16 bytes verbatim (no repack)
      - Otherwise, re-encode from "<HEX15> CommandName [params]" text
    Returns:
      recs: bytearray of all 16-byte records in sequence
      idx:  index in `lines` where sysmem header appears
    """
    recs = bytearray()
    idx = 0

    while idx < len(lines):
        ln = lines[idx].rstrip("\n")
        strip_ln = ln.strip()

        # Skip blank lines or comments
        if not strip_ln or strip_ln.startswith("#"):
            idx += 1
            continue

        # Stop as soon as we hit the SysMem header
        if strip_ln.startswith("===== SysMem (400 bytes) as raw hex ====="):
            break

        # If "# raw:" is present, just take those 16 bytes verbatim
        if "# raw:" in ln:
            # Extract 32 hex chars after "# raw:"
            main_part, raw_part = ln.split("# raw:", 1)
            raw_hex = raw_part.strip().replace(" ", "")
            if len(raw_hex) != 32:
                raise ValueError(
                    f"Expected 32 hex chars after '# raw:', got '{raw_hex}' in line: '{ln}'"
                )
            rec = bytes.fromhex(raw_hex)
            if len(rec) != 16:
                raise ValueError(
                    f"Raw hex did not decode to 16 bytes in line: '{ln}'"
                )
            recs.extend(rec)
            idx += 1
            continue

        # 2) No "# raw:" → parse & re-pack from text
        rec = _pack_record_from_text(ln, ln)
        recs.extend(rec)
        idx += 1

    return recs, idx


def _pack_record_from_text(text_part, original_line):
    """
    Given text_part = "<HEX15> <CommandName> [param1 param2 ...]" (no "# raw:"),
    parse tokens and pack into 16-byte record

    Returns a bytes object of length 16. Raises ValueError on parse failures.
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

    # If byte15 = 0xFF, the record is padding
    if byte15 == 0xFF:
        return b"\x00" * 15 + b"\xFF"

    # Otherwise build a 16-byte buffer with b[15] = byte15
    b = bytearray(16)
    b[15] = byte15

    # Split tokens[1:] into command name vs numeric parameters
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

    # Convert param_tokens to a list of numbers
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

    # Re-encode data

    if cmd_id == 54:
        p = int(val_list[vi]); vi += 1
        struct.pack_into("<h", b, 12, p)

    elif cmd_id == 1:
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 0, f0)
        p1 = int(val_list[vi]); vi += 1
        b[14] = p1

    elif cmd_id in (9, 71):
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 0, f0)

    elif cmd_id in (27, 30, 40):
        p = int(val_list[vi]); vi += 1
        struct.pack_into("<h", b, 12, p)

    elif cmd_id in (33, 76):
        p = int(val_list[vi]); vi += 1
        b[14] = p

    elif cmd_id == 22:
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 0, f0)
        p1 = int(val_list[vi]); vi += 1
        b[14] = p1

    elif cmd_id in (6, 53):
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 0, f0)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 4, f1)

    elif cmd_id == 68:
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 0, f0)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 4, f1)
        f2 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 8, f2)

    elif cmd_id == 36:
        p = int(val_list[vi]); vi += 1
        struct.pack_into("<h", b, 12, p)
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 0, f0)

    elif cmd_id == 28:
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 0, f0)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 4, f1)
        p2 = int(val_list[vi]); vi += 1
        b[14] = p2 - 1
        p3 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", b, 12, p3)

    elif cmd_id == 70:
        p = int(val_list[vi]); vi += 1
        struct.pack_into("<h", b, 8, p)
        p2 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", b, 10, p2)

    elif cmd_id in (7, 43):
        p = int(val_list[vi]); vi += 1
        struct.pack_into("<h", b, 8, p)
        p2 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", b, 10, p2)
        p3 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", b, 12, p3)

    elif cmd_id == 69:
        p = int(val_list[vi]); vi += 1
        struct.pack_into("<h", b, 8, p)
        p2 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", b, 10, p2)

    elif cmd_id == 23:
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 0, f0)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 4, f1)
        f2 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 8, f2)

    elif cmd_id in (2, 3, 4, 5, 12, 18, 31, 55, 67, 72, 73, 74, 75):
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 0, f0)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 4, f1)
        f2 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 8, f2)

    elif cmd_id == 66:
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 0, f0)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 4, f1)
        f2 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 8, f2)
        p3 = int(round(val_list[vi] * 100)); vi += 1
        struct.pack_into("<h", b, 12, p3)

    elif cmd_id == 21:
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 0, f0)
        p2 = int(round(val_list[vi] * 1000)); vi += 1
        struct.pack_into("<h", b, 10, p2)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 4, f1)
        p4 = int(round(val_list[vi] * 1000)); vi += 1
        struct.pack_into("<h", b, 12, p4)
        p5 = int(round(val_list[vi] * 1000)); vi += 1
        struct.pack_into("<h", b, 8, p5)

    elif cmd_id == 37:
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 0, f0)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 4, f1)
        f2 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 8, f2)
        p4 = int(round(val_list[vi] * 100)); vi += 1
        struct.pack_into("<h", b, 12, p4)

    elif cmd_id in (29, 38):
        f0 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 0, f0)
        f1 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 4, f1)
        f2 = float(val_list[vi]); vi += 1
        struct.pack_into("<f", b, 8, f2)
        p3 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", b, 12, p3)

    elif cmd_id in (13, 32):
        p1 = int(round(val_list[vi] * 100)); vi += 1
        struct.pack_into("<h", b, 0, p1)
        p2 = int(round(val_list[vi] * 100)); vi += 1
        struct.pack_into("<h", b, 2, p2)
        p3 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", b, 10, p3)
        p4 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", b, 12, p4)
        p5 = int(val_list[vi]); vi += 1
        b[14] = p5
        p6 = int(val_list[vi]); vi += 1
        struct.pack_into("<h", b, 8, p6)

    return bytes(b)


def parse_raw_sysmem(lines, start_idx):
    """
    Starting below sysmem header, read next 400 bytes (20 bytes per line). Return (sysmem_bytes, next_idx).
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
        raise ValueError("Could not parse 400 bytes of raw SysMem.")
    return bytes(hex_bytes[:400]), idx


def decode_file(infile, outfile):
    data = open(infile, "rb").read()
    if len(data) < 500:
        print("Error: file too small (<500 bytes).")
        sys.exit(1)

    lines = []
    sysmem = decode_command_records(data, lines)
    decode_sysmem(sysmem, lines)

    with open(outfile, "w", encoding="utf-8") as fout:
        fout.write("\n".join(lines))

    print(f"Decoded {infile} → {outfile}")


def encode_file(infile, outfile):
    all_lines = open(infile, "r", encoding="utf-8").read().splitlines()

    recs, idx = encode_records_from_text(all_lines)

    # Find sysmem header
    while idx < len(all_lines) and not all_lines[idx].startswith("===== SysMem (400 bytes) as raw hex ====="):
        idx += 1
    if idx >= len(all_lines):
        raise ValueError("Raw sysmem header not found in input text.")

    sysmem, _ = parse_raw_sysmem(all_lines, idx)

    with open(outfile, "wb") as f:
        f.write(recs)
        f.write(sysmem)

    print(f"Encoded {infile} → {outfile}")


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
