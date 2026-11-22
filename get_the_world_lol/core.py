import win32pipe, win32file
import numpy as np
import base64
import json, time


def read_pipe():
    pipe = None
    print("waiting for game to create pipe...")
    while pipe is None:
        try:
            pipe = win32file.CreateFile(
                r"\\.\pipe\unrandom_pipe",
                win32file.GENERIC_READ,
                0,
                None,
                win32file.OPEN_EXISTING,
                0,
                None,
            )
        except Exception:
            time.sleep(0.5)

    print("connected!!")
    buf = ""
    try:
        while True:
            _, data = win32file.ReadFile(pipe, 65536)
            buf += data.decode("utf-8")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                if line.strip():
                    msg = json.loads(line)
                    raw_handle_pipe(msg)
    except Exception as e:
        print(f"pipe closed: {e}")
    finally:
        win32file.CloseHandle(pipe)


def raw_handle_pipe(msg):
    t = msg.get("type")
    if t == "boot":
        print(f"[boot] unity {msg['unity_version']} | scene={msg['scene']}")
    elif t == "worldblocks":
        handle_worldblocks(msg)


def handle_worldblocks(msg):
    w, h = msg["width"], msg["height"]
    biome_depth = msg.get("biome_depth")
    raw = base64.b64decode(msg["data"])
    arr = np.frombuffer(raw, dtype=np.uint16).reshape((w, h))

    ts = int(time.time())
    out_path = f"worldblocks_depth{biome_depth}_{ts}.npy"
    np.save(out_path, arr)

    uniques = np.unique(arr)
    print(f"[worldblocks] depth={biome_depth} {w}x{h} ({len(raw)} bytes) -> {out_path}")
    print(
        f"[worldblocks] unique block ids: {uniques[:20]}{'...' if len(uniques) > 20 else ''}"
    )


if __name__ == "__main__":
    read_pipe()
