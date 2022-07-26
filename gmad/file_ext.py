from typing import Literal, BinaryIO

from chardet import detect


class File:
    file: BinaryIO

    def __init__(self, file: BinaryIO):
        self.file = file

    def __getattr__(self, attr):
        return getattr(self.file, attr)

    def __iter__(self):
        return iter(self.file)

    def read_null(self) -> bytes:
        """Read a file pointer until it reaches a null byte, returning an array of byte objects."""
        return_data = b""
        next_byte = self.file.read(1)
        while next_byte != b"\x00":
            return_data += next_byte
            next_byte = self.file.read(1)
        return return_data

    def read_null_string(self) -> str:
        """Read a null terminated string from a filer pointer, returning the read string."""
        raw = self.read_null()
        cset = detect(raw)['encoding']
        if cset is None:
            cset = "ascii"
        return raw.decode(cset)

    def read_string(self, length: int = 0) -> str:
        """Return a string of given length pulled from the file."""
        raw = self.file.read(length)
        cset = detect(raw)['encoding']
        if cset is None:
            cset = "ascii"
        return raw.decode(cset)

    def read_int(self, length: int = 4, edian: Literal['little', 'big'] = 'little'):
        """Read integer from file, returning an int of byte length and edian encoding."""
        return int.from_bytes(self.file.read(length), edian)
