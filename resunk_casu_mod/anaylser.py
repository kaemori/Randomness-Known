import itertools
from pathlib import Path

logfile = Path().cwd() / "pycore.log"
filfile = Path().cwd() / "pycore_filtered.log"
blacklist = (
    "{'min': 0.75, 'max': 1.25}",
    "{'min': 0.0, 'max': 0.0}",
    "{'min': 0.0, 'max': 1.0}",
    "{'min': 1, 'max': 5}",
    "{'min': 0, 'max': 2147483647}",
    "{'min': 0, 'max': 1024}",
    "{'min': 3, 'max': 5}",
    "{'min': 0.35, 'max': 0.5}",
    "{'min': 6, 'max': 64}",
    "{'min': 6, 'max': 60}",
    "{'min': 0.35, 'max': 0.4}",
    "{'min': 6, 'max': 48}",
    "{'min': 0, 'max': 2}",
    "{'min': 0.25, 'max': 0.3}",
    "{'min': 0.24, 'max': 0.3}",
    "{'min': 0.5, 'max': 0.6}",
    "{'min': 4, 'max': 16}",
    "{'min': -0.1, 'max': 0.1}",
)
startlog = False
last = 1794220888.5743024
with open(filfile, "w") as f:
    for timeline, placeline in itertools.batched(logfile.read_text().splitlines(), 2):
        timeof = float(timeline.split(maxsplit=1)[0].strip("[]"))
        if startlog:
            for phrase in blacklist:
                if phrase in timeline:
                    break
            else:
                f.write(f"({(timeof-last) * 1000}) {timeline}\n{placeline}\n\n")
                last = timeof

        elif timeof > 1794220888.5743024:
            startlog = True
