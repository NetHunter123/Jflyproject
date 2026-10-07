"""Stream the SimScale solution zip and keep only the wall mesh and U.

The URL comes from the environment variable SIMSCALE_URL. Nothing else from
the archive is written to disk. Output directory: SIMSCALE_OUT, or
%TEMP%\\gnplus-A-fine.
"""
import os
import struct
import sys
import time
import urllib.request
import zlib

def keep(name):
    norm = name.replace("\\", "/")
    base = norm.rsplit("/", 1)[-1]
    if "/polyMesh/" in norm and base in (
        "boundary", "boundary.gz", "points", "points.gz",
        "faces", "faces.gz", "owner", "owner.gz",
    ):
        return True
    if base in ("wallShearStress.gz", "yPlus.gz", "wallShearStress", "yPlus"):
        return True
    return False


class Prefix:
    def __init__(self, data, raw):
        self.data = data
        self.raw = raw

    def read(self, n):
        if self.data:
            take, self.data = self.data[:n], self.data[n:]
            if len(take) == n:
                return take
            return take + self.raw.read(n - len(take))
        return self.raw.read(n)


def read_exact(stream, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = stream.read(n - len(buf))
        if not chunk:
            raise EOFError(f"short read, wanted {n}, got {len(buf)}")
        buf += chunk
    return bytes(buf)


def zip64_sizes(extra, need_comp, need_uncomp):
    i = 0
    comp = uncomp = None
    while i + 4 <= len(extra):
        hid, hlen = struct.unpack_from("<HH", extra, i)
        i += 4
        payload = extra[i:i + hlen]
        i += hlen
        if hid != 1:
            continue
        off = 0
        if need_uncomp:
            uncomp = struct.unpack_from("<Q", payload, off)[0]
            off += 8
        if need_comp:
            comp = struct.unpack_from("<Q", payload, off)[0]
            off += 8
    return comp, uncomp


def main():
    url = os.environ["SIMSCALE_URL"]
    out = os.environ.get("SIMSCALE_OUT") or os.path.join(os.environ["TEMP"], "gnplus-A-fine")
    os.makedirs(out, exist_ok=True)
    log_path = os.path.join(out, "members.txt")
    req = urllib.request.Request(url, headers={"User-Agent": "gnplus-shear"})
    started = time.time()
    seen = 0
    saved = []
    with urllib.request.urlopen(req, timeout=120) as stream, open(log_path, "w", encoding="utf-8") as log:
        while True:
            sig = stream.read(4)
            if not sig:
                break
            if sig != b"PK\x03\x04":
                # Central directory or end of archive. The members we need
                # are already stored; stop without reading the rest.
                log.write(f"STOP {sig.hex()} after {seen} bytes\n")
                log.flush()
                break
            hdr = read_exact(stream, 26)
            ver, flag, method, _t, _d, crc, comp, uncomp, nlen, elen = struct.unpack("<HHHHHIIIHH", hdr)
            name = read_exact(stream, nlen).decode("utf-8", "replace")
            extra = read_exact(stream, elen) if elen else b""
            if comp == 0xFFFFFFFF or uncomp == 0xFFFFFFFF:
                zcomp, zuncomp = zip64_sizes(extra, comp == 0xFFFFFFFF, uncomp == 0xFFFFFFFF)
                if zcomp is not None:
                    comp = zcomp
                if zuncomp is not None:
                    uncomp = zuncomp
            seen += 30 + nlen + elen + comp
            log.write(f"{method}\t{comp}\t{uncomp}\t{flag}\t{name}\n")
            log.flush()
            print(name, flush=True)
            dest = None
            if keep(name) and not name.endswith("/"):
                rel = name.replace("\\", "/").lstrip("/")
                dest = os.path.join(out, rel.replace("/", os.sep))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
            if method == 8 and (flag & 8) and comp == 0:
                dec = zlib.decompressobj(-15)
                out_fh = open(dest, "wb") if dest else None
                pending = b""
                try:
                    while not dec.eof:
                        if not pending:
                            pending = stream.read(1024 * 1024)
                            if not pending:
                                raise EOFError(name)
                        produced = dec.decompress(pending)
                        pending = b""
                        if out_fh and produced:
                            out_fh.write(produced)
                    if out_fh:
                        out_fh.write(dec.flush())
                finally:
                    if out_fh:
                        out_fh.close()
                pending = dec.unused_data + pending
                if pending[:4] == b"PK\x07\x08":
                    pending = pending[4:]
                desc_len = 20 if ver >= 45 else 12
                if len(pending) < desc_len:
                    pending += read_exact(stream, desc_len - len(pending))
                rest = pending[desc_len:]
                if rest[:4] not in (b"PK\x03\x04", b"PK\x01\x02", b"PK\x05\x06", b"PK\x06\x06", b""):
                    print("misaligned after", name, rest[:12].hex(), file=sys.stderr)
                    sys.exit(3)
                if rest:
                    stream = Prefix(rest, stream)
                if dest is not None:
                    saved.append(name)
                    print(f"saved {name}", flush=True)
            else:
                if flag & 8 and comp == 0:
                    print("data descriptor without size, cannot skip", name, file=sys.stderr)
                    sys.exit(2)
                dec = zlib.decompressobj(-15) if (dest is not None and method == 8) else None
                with open(dest, "wb") if dest else open(os.devnull, "wb") as fh:
                    left = comp
                    while left:
                        chunk = stream.read(min(left, 8 * 1024 * 1024))
                        if not chunk:
                            raise EOFError(name)
                        left -= len(chunk)
                        if dest is None:
                            continue
                        fh.write(dec.decompress(chunk) if dec else chunk)
                    if dec:
                        fh.write(dec.flush())
                if dest is not None:
                    saved.append(name)
                    print(f"saved {name} ({uncomp} bytes)", flush=True)
            if method not in (0, 8):
                print("unexpected method", method, name, file=sys.stderr)
            mb = seen / 1e6
            if int(mb) % 500 < 1:
                rate = seen / (time.time() - started + 1e-6) / 1e6
                print(f"{mb:.0f} MB  {rate:.1f} MB/s  {name}", flush=True)
    print("DONE", len(saved), "files", flush=True)
    for name in saved:
        print(" ", name, flush=True)


if __name__ == "__main__":
    main()
