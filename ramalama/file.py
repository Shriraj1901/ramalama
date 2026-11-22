from __future__ import annotations

# The following code is inspired from: https://github.com/ericcurtin/lm-pull/blob/main/lm-pull.py
import json
import os
import platform

# Import platform-specific locking mechanisms
if platform.system() != "Windows":
    import fcntl

# A YAML parser rejects DEL and the C1 controls, and reads the next line and
# the line and paragraph separators as line breaks. A JSON string leaves all
# of them as they are.
_YAML_ESCAPES = {code: f"\\u{code:04x}" for code in (*range(0x7F, 0xA0), 0x2028, 0x2029)}


def yaml_quote(value: str) -> str:
    """Serialize a string as a YAML double quoted scalar.

    A JSON string is a valid YAML double quoted scalar. It escapes the quote,
    the backslash and the control characters that would otherwise end the
    scalar early or be read as an escape. The few characters a YAML parser
    does not accept as they are, or takes for line breaks, are escaped as well.
    """
    return json.dumps(value, ensure_ascii=False).translate(_YAML_ESCAPES)


class File:
    def __init__(self):
        self.file = None
        self.fd = -1

    def open(self, filename, mode):
        self.file = open(filename, mode)
        return self.file

    def lock(self):
        if self.file:
            self.fd = self.file.fileno()
            if platform.system() != "Windows":
                try:
                    # Unix file locking using fcntl
                    fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except (BlockingIOError, OSError):
                    self.fd = -1
                    return 1
        return 0

    def __del__(self):
        if self.fd >= 0:
            if platform.system() != "Windows":
                try:
                    # Unlock on Unix
                    fcntl.flock(self.fd, fcntl.LOCK_UN)
                except OSError:
                    pass  # File may already be closed

        if self.file:
            self.file.close()


class PlainFile:
    def __init__(self, filename: str, content: str = ""):
        self.filename = filename
        self.content = content

    def write(self, dirpath: str):
        dirpath = os.path.expanduser(dirpath)
        with open(os.path.join(dirpath, self.filename), "w") as f:
            f.write(self.content)
            f.flush()


class UnitFile:
    def __init__(self, filename: str):
        self.filename = filename
        self.sections: dict[str, dict[str, list[str]]] = {}

    def add(self, section: str, key: str, value: str = ""):
        if section not in self.sections:
            self.sections[section] = {}
        if key not in self.sections[section]:
            self.sections[section][key] = []
        self.sections[section][key].append(value)

    def write(self, dirpath: str):
        dirpath = os.path.expanduser(dirpath)
        with open(os.path.join(dirpath, self.filename), "w") as f:
            self._write(f)

    def _write(self, f):
        comments = self.sections.get('comment', {})
        for section in comments:
            f.write(f'{section}\n')

        for section, section_items in self.sections.items():
            if section == "comment":
                continue
            f.write(f'[{section}]\n')
            for key, values in section_items.items():
                for value in values:
                    f.write(f'{key}={value}\n')
            f.write('\n')
