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
        # print(f"[boot] unity {msg['unity_version']} | scene={msg['scene']}")
        print("")
    elif t == "call":
        fn = msg["fn"]
        args = msg["args"]
        result = msg["result"]
        state = msg["state"]
        stack = msg.get("stack", None)

        if fn == "random.insideunitcircle":
            import math

            mag = math.sqrt(result["x"] ** 2 + result["y"] ** 2)
            if abs(mag - 1.0) < 0.001:
                fn = "random.insideunitcircle.normalized"

        handle_random(fn, args, result, state, stack)


# randomness magic
last_state = None


def handle_random(fn, args, result, state, stack):
    if stack is None:
        stack = []

    logline = (
        f"[{time.time()}] {fn} w/ {args} r:{result}, ({state})\n{json.dumps(stack)}\n"
    )
    print(logline, end="")
    logfile.write(logline)


with open("pycore.log", "w") as logfile:
    read_pipe()  # calls handle_random

# from static analysis
# Body.HandleVisuals:3246 limb.transform.position += new vector3(random.range(-num5, num5), random.range(-num5, num5));
# note: only runs when standing

# num5:
# +0.0004 * averagePain if averagePain > 75f  // pain
# +0.025 if actualOpiateReception < -25f  // withdrawal (from num4)
# +0.01 * (timeWasStill - 20f) if timeWasStill > 20f  // self harm events (from num4)
# <add shake events (i.e. idle, water, cogpairment)> (from num4)
# +0.025 if temperature < 32.5f  // shivering (from num4)

# Talker.LateUpdate.cs:448 this.text.recttransform.position = (this.body ? (this.body.limbs[0].transform.position + vector3.up * 4f + random.insideunitcircle * this.body.averagepain * 0.0025f + vector3.back * 2.6f) : (base.transform.position + vector3.up * 3f + vector3.back * 2.6f));
# runs every frame, cannot be skipped
