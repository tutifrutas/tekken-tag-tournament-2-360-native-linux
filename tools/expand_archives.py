"""Read expanded archive sizes from an owner-supplied nrfo index."""
import struct

LZX_MAGIC = b"\x0f\xf5\x12\xed"


def read_boxes(record: bytes) -> dict:
    boxes, offset = {}, 0
    while offset + 8 <= len(record):
        size = struct.unpack_from(">I", record, offset)[0]
        kind = record[offset + 4:offset + 8].decode("latin1", "replace")
        boxes[kind] = (offset, size)
        if size < 8:
            break
        offset += size
    return boxes


def expected_sizes(nrfo_path: str, names: list) -> dict:
    """Expanded size of each archive is max(ofsd) + 256 in its nrfo record."""
    with open(nrfo_path, "rb") as stream:
        data = stream.read()
    count = struct.unpack_from(">I", data, 0)[0]
    result = {}
    for index in range(min(count, len(names))):
        offset, size = struct.unpack_from(">II", data, 4 + index * 8)
        if not size:
            result[names[index]] = None
            continue
        record = data[offset:offset + size]
        boxes = read_boxes(record)
        if "ofsd" not in boxes:
            result[names[index]] = None
            continue
        start, length = boxes["ofsd"]
        values = [struct.unpack_from(">I", record, start + 8 + item * 4)[0]
                  for item in range((length - 8) // 4)]
        result[names[index]] = (max(values) if values else 0) + 256
    return result
