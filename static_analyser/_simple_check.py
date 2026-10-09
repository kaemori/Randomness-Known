# simply loops through every file and checks each line for "random."

from pathlib import Path
import re

from helpers.function_getter import (
    load_modules,
    load_module_index,
)

from helpers.logging_helper import logger

DECOMPILED_PATH = Path(__file__).parent / "Assembly-CSharp"
ALL_MODULES = load_modules(DECOMPILED_PATH)
MODULE_INDEX = load_module_index(ALL_MODULES)

delimiters = [" ", "(", ")", "{", "}", "[", "]", ";", ",", ":", '"', "'"]
reg = "|".join(map(re.escape, delimiters))
random_types = set()

for module_name, lines in ALL_MODULES.items():
    with open(DECOMPILED_PATH / f"{module_name}.cs", "r", encoding="utf-8") as f:
        for line in f:
            line = line.lower()
            if "random." in line:
                parts = re.split(reg, line)
                for part in parts:
                    if "random." in part:
                        random_types.add(part.strip())

print(random_types)
