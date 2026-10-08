import win32pipe, win32file
import hashlib
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
            _, data = win32file.ReadFile(pipe, 4096)
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
    elif t == "call":
        fn = msg["fn"]
        args = msg["args"]
        result = msg["result"]
        state = msg["state"]

        if fn == "random.insideunitcircle":
            import math

            mag = math.sqrt(result["x"] ** 2 + result["y"] ** 2)
            if abs(mag - 1.0) < 0.001:
                fn = "random.insideunitcircle.normalized"

        handle_random(fn, args, result, state)


# randomness magic
last_state = None


def handle_random(fn, args, result, state):
    logline = f"{fn} w/ {args} r:{result}, ({state})"
    print(logline)
    logfile.write(logline + "\n")


with open("pycore.log", "w") as logfile:
    read_pipe()  # calls handle_random
