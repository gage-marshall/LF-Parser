# LF-Parser

A clean-room Python tool for decoding and encoding Fisnar `.LF` motion-control files in editable plain-text, with byte-perfect round-trip fidelity. Users can open a `.LF` file, make adjustments to commands or parameters, and save back to a valid `.LF` without touching raw hex.

This project is released under the MIT License.

> **Disclaimer**  
> This project is an independent reverse-engineering effort and is **not affiliated with, endorsed by, or supported by Fisnar Inc.**  
> All trademarks, product names, and company names or logos are the property of their respective owners. This tool is provided for educational and interoperability purposes under fair use.

## Table of Contents

- Features

- Prerequisites

- Installation

- Usage

  - Decoding an `LF` file
  - Editing the decoded text
  - Re-encoding to `LF`

- File Format Overview

- Command Reference

- Licensing

- Contributing

- Acknowledgements

  

## Features

- **Byte-perfect round-trip**: Decode → edit → encode without altering any bytes unless you explicitly change a command or parameter.

- **Editable plain-text**: Each 16-byte record is presented as

  ```
  XX CommandName [param1 param2 …]    # raw: <32 hex chars>
  ```

  allowing users to see both human-readable data and exact raw hex.

- **Automatic raw-hex alignment**: All `# raw:` comments start at a fixed column for neat readability.

- **Selective repacking**: If you remove a record's `# raw:` comment, the encoder will re-pack that record from your edited parameters, otherwise it reuses the original 16 bytes verbatim.

- **SysMem decoding/encoding**: The last 400 bytes (machine parameters) can be viewed in raw hex and as human-readable fields, then preserved exactly on re-encode.

- **MIT-licensed**: Fully open-source, no vendor code included; safe for redistribution and modification.

  

## Prerequisites

- Python 3.6 or later

- No external dependencies (uses only built-in `struct`, `argparse`, etc.)

  

## Installation

1. **Clone this repository** (or download `lf-parser.py` directly):

   ```
   git clone https://github.com/gage-marshall/LF-Parser.git
   cd LF-Parser
   ```

2. **(Optional) Make it executable** (on Linux/macOS):

   ```
   chmod +x lf-parser.py
   ```

3. **Verify** that Python 3 is available:

   ```
   python3 --version
   ```



## Usage

### Decoding an LF file

To decode a `.LF` file into human-editable text:

```
python3 lf-parser.py -d input.LF -o output.txt
```

Example:

```
$ python3 lf-parser.py -d PROG.LF -o PROG.txt
Decoded PROG.LF → PROG.txt
```

- `input.LF` is your original Fisnar `.LF` file.

- `output.txt` will be a UTF-8 text file containing:

  1. One 16-byte record per line, formatted as

     ```
     XX CommandName [params…]    # raw: <32 hex chars>
     ```

  2. A `===== SysMem (400 bytes) as raw hex =====` section (20 bytes per line).

  3. A `===== SysMem (decoded fields) =====` section showing parameter names and values.

### Editing the decoded text

Open `output.txt` in your favorite editor (VS Code, Notepad++, etc.). You will see lines like:

```
00 Empty                                                   # raw: 00000000000000000000000000000000
23 Home Point                                              # raw: 00000000000000000000000000000023
17 Dispense End Setup 6 1 1                                # raw: 0000C0400000803F0000803F00000017
```

- **To modify a record**: remove its `# raw:` comment and adjust the `XX CommandName` or numeric `params`. On re-encode, that record will be re-packed from your edited values.
- **To leave a record unchanged**: do not touch its `# raw:`. The encoder will detect the comment and write those 16 raw bytes verbatim.
- **To modify a SysMem field**: either edit the raw hex under "`SysMem (400 bytes) as raw hex`" directly or change the human-readable value under "`SysMem (decoded fields)`" and re-pack it (see warning below).

> **Tip**: If you edit a SysMem value under the "decoded fields" section, you must also regenerate its raw hex. Currently, the encoder does not recalculate SysMem from the decoded fields; it simply rewrites the raw 400 bytes.

### Re-encoding to LF

Once you're satisfied with your edits:

```
python3 lf-parser.py -e edited.txt -o new_program.LF
```

Example:

```
$ python3 lf-parser.py -e PROG.txt -o PROG-N.LF
Encoded PROG.txt → PROG-N.LF
```

- Any record whose `# raw:` was left intact → identical 16 bytes.
- Any record whose `# raw:` was removed → re-packed from plain-text parameters.
- The final 400 bytes of SysMem are copied verbatim from the "`# raw:`" hex block.

Verifying byte-perfect round-trip (no changes to the text):

```
$ md5sum PROG.LF
7576b846f3c03b1fae1998e1759668f9  PROG.LF
$ md5sum PROG-N.LF
7576b846f3c03b1fae1998e1759668f9  PROG-N.LF
$ diff PROG5.LF PROG5-N.LF
# (no output → identical)
```

## File Format Overview

A Fisnar `.LF` file is composed of:

1. **A sequence of 16-byte records** (commands), each of which encodes:
   - Bytes 0–3: `float32` or unused (depends on `cmd_id`)
   - Bytes 4–7: `float32` or unused
   - Bytes 8–11: `float32` or unused (or `int16` in some commands)
   - Bytes 12–13: `int16` (for certain commands)
   - Byte 14: `uint8` (extra parameter or flag for certain commands)
   - Byte 15: `cmd_id` (low 7 bits = command ID, high bit is a "comment" flag)
2. **A 400-byte SysMem block** appended at the end, containing machine parameters (tool offsets, speeds, counters, flags, etc.).
   - Always exactly 400 bytes.
   - Can be viewed both as raw hex (20 bytes/line) and as decoded fields (e.g., `ProgramSize`, `XYMoveSpeed`, `O1…O8`, etc.).



## Licensing

This project is released under the **MIT License**. See below for the full text.

```
MIT License

Copyright 2025 Gage Marshall

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

```

## Contributing

Contributions are welcome! If you'd like to:

- Add support for more command IDs
- Improve parameter validation or text formatting
- Provide additional examples or sample `.LF` files

… please open an issue or submit a pull request.

## Acknowledgements

- Special thanks to everyone who tested this parser with real `.LF` programs and provided feedback on edge cases (e.g., unusual command IDs, padding scenarios).

Enjoy editing your Fisnar `.LF` programs directly in plain text!