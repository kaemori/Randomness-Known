import time


def tail_f(path):
    with open(path, "r") as f:
        f.seek(0, 2)  # seek to end of file
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            print(line, end="")


tail_f(r"C:\Users\magnolia\Desktop\Stuff\Game files\CasU7\BepInEx\LogOutput.log")
