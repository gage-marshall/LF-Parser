# LF-Parser

A clean-room Python tool for decoding and encoding Fisnar `.LF` motion-control files in editable plain-text, with byte-perfect round-trip fidelity. Users can open a `.LF` file, make adjustments to commands or parameters, and save back to a valid `.LF` without touching raw hex.

This project is released under the MIT License.

**Disclaimer**
This project is an independent reverse-engineering effort and is **not affiliated with, endorsed by, or supported by Fisnar Inc.**
All trademarks, product names, and company names or logos are the property of their respective owners. This tool is provided for educational and interoperability purposes under fair use.

## Features

- **Byte-perfect round-trip**: Decode → edit → encode without altering any bytes unless you explicitly change a command or parameter.

- **Editable plain-text**: Each 16-byte record is presented as:

  `XX CommandName [param1 param2 …]    # raw: <32 hex chars>`

  allowing users to see both human-readable data and exact raw hex.

- **Automatic raw-hex alignment**: All `# raw:` comments start at a fixed column for neat readability.

- **Selective repacking**: If you remove a record’s `# raw:` comment, the encoder will re-pack that record from your edited parameters; otherwise it reuses the original 16 bytes verbatim.

- **SysMem decoding/encoding**: The last 400 bytes (machine parameters) are split into two sections:

  - **Decoded fields**: Named SysMem fields (like `ProgramSize`, `TipHomeX`, `O1`, etc.) are decoded and aligned with individual `# raw:` comments.
  - **Unmapped raw block**: Any remaining (unmapped) bytes are preserved in a 400-byte raw block at the end.

- **MIT-licensed**: Fully open-source, safe for redistribution and modification.

## Usage

### Decoding

```
python3 lf-parser.py -d input.LF -o output.txt
```

- Reuses original record bytes when `# raw:` is present.
- Re-encodes parameters only when `# raw:` is removed.
- Field lines include: `FieldName: value    # raw: <hex>`
- A 400-byte block preserves unmapped SysMem bytes.

### Editing

- To modify a record, remove the `# raw:` and change the readable values.
- To keep original bytes, leave `# raw:` intact.
- Same applies for SysMem field lines.

### Encoding

```
python3 lf-parser.py -e input.txt -o output.LF
```

- Reconstructs `.LF` with original bytes unless edits are made.
- Preserves all bytes—including unmapped—unless `# raw:` is removed.

### Verifying No Changes

```
sha256sum PROG.LF
sha256sum PROG-N.LF
```

If no edits were made or `# raw:` was left intact, hashes will match.

## Command Reference

| Byte (Hex) | Command Name          | Parameters                                          |
| ---------- | --------------------- | --------------------------------------------------- |
| 00         | Empty                 |                                                     |
| 01         | Line Speed            | float speed, int mode                               |
| 02         | Line Passing          | float x, float y, float z                           |
| 03         | Arc Point             | float x, float y, float z                           |
| 04         | Line Start            | float x, float y, float z                           |
| 05         | Dispense Dot          | float x, float y, float z                           |
| 06         | Output                | float x, float y                                    |
| 07         | Input                 | int16 p1, int16 p2, int16 p3                        |
| 09         | Wait Point            | float time                                          |
| 11         | End Program           |                                                     |
| 12         | Line End              | float x, float y, float z                           |
| 13         | Step & Repeat X       | float dx, float dy, int n, addr, int mode, int step |
| 18         | Stop Point            | float x, float y, float z                           |
| 19         | Empty (type 2)        |                                                     |
| 20         | Point Dispense Setup  |                                                     |
| 21         | Line Dispense Setup   | float x, float p1, float y, float p2, float p3      |
| 22         | Z Clearance           | float z, int mode                                   |
| 23         | Dispense End Setup    | float x, float y, float z                           |
| 27         | Goto Address          | int16 addr                                          |
| 28         | Brush Area            | float x, float y, int count, int addr               |
| 29         | Call Subroutine       | float x, float y, float z, int addr                 |
| 30         | Call Program          | int16 addr                                          |
| 31         | Dummy Point CP        | float x, float y, float z                           |
| 32         | Step & Repeat Y       | same as 13                                          |
| 33         | Dispense ON/OFF       | int flag                                            |
| 35         | Home Point            |                                                     |
| 36         | Loop Address          | int16 addr, float value                             |
| 37         | Circle                | float x, float y, float z, float radius             |
| 38         | Retract Setup         | float x, float y, float z, int addr                 |
| 39         | Initialize            |                                                     |
| 40         | Label                 | int16 label                                         |
| 43         | Acceleration          | int16 p1, int16 p2, int16 p3                        |
| 51         | Blend Point           |                                                     |
| 53         | Circle Dispense Setup | float x, float y                                    |
| 54         | Dispense Outport      | int16 port                                          |
| 55         | Dummy Point PTP       | float x, float y, float z                           |
| 57         | Cubical Layer         |                                                     |
| 66         | Height Sensor Point   | float x, float y, float z, float height             |
| 67         | Pause Point           | float x, float y, float z                           |
| 68         | Output Toggle         | float a, float b, float c                           |
| 69         | Wait Input            | int16 p1, int16 p2                                  |
| 70         | Check Block           | int16 p1, int16 p2                                  |
| 71         | Acc Time              | float time                                          |
| 72         | Dummy Start           | float x, float y, float z                           |
| 73         | Dummy Passing         | float x, float y, float z                           |
| 74         | Dummy Arc             | float x, float y, float z                           |
| 75         | Dummy End             | float x, float y, float z                           |
| 76         | Fixed Point           | int flag                                            |
| 127        | Padding               |                                                     |

## SysMem Field Reference

| Field Name            | Offset | Type      | Notes / Transform                    |
| --------------------- | ------ | --------- | ------------------------------------ |
| ProgramSize           | 207    | int32     | stored as (value + 1)                |
| XYMoveSpeed           | 12     | float32   |                                      |
| ZMoveSpeed            | 44     | float32   |                                      |
| DebugSpeed            | 105    | float32   |                                      |
| TipHomeX              | 85     | float32   |                                      |
| TipHomeY              | 89     | float32   |                                      |
| TipHomeZ              | 93     | float32   |                                      |
| TipAdjustX            | 109    | float32   |                                      |
| TipAdjustY            | 113    | float32   |                                      |
| TipAdjustZ            | 117    | float32   |                                      |
| SoftOrgX              | 267    | float32   |                                      |
| SoftOrgY              | 271    | float32   |                                      |
| SoftOrgZ              | 275    | float32   |                                      |
| AutoPurgeWaitTime     | 178    | float32   |                                      |
| AutoPurgeDispenseTime | 182    | float32   |                                      |
| ZLimit                | 79     | float32   |                                      |
| PreDispenseWait       | 263    | float32   |                                      |
| RunCounter            | 70     | int16     |                                      |
| QuickStep             | 177    | int8      | 1 if True, 0 otherwise               |
| RunningHomeFirst      | 397    | int8      | stored as (0 if True, 1 otherwise)   |
| EmergencyMode         | 190    | int8      | "Maintaining"=1, "Initial"=0         |
| ProgramLabel          | 52     | str[15]   | zero-terminated ASCII                |
| MagicSignature_398    | 398    | int16     |                                      |
| O1–O8 (bitflags)      | 83     | bit0–bit7 | encoded in a 16-bit int at offset 83 |

## License

MIT License

```
MIT License

Copyright 2025 Gage Marshall

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the “Software”), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Acknowledgements

Thanks to all contributors and testers who ensured that field-level editing, `# raw:` preservation, and byte-perfect encoding behave consistently and predictably.