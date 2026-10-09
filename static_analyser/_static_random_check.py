from pathlib import Path
import re

from function_getter import (
    load_modules,
    load_module_index,
    get_function_body,
    find_function_lines,
)

DECOMPILED_PATH = Path(__file__).parent / "Assembly-CSharp"
ALL_MODULES = load_modules(DECOMPILED_PATH)
MODULE_INDEX = load_module_index(ALL_MODULES)

MODULE_TO_INSPECT = "Talker"
FUNCTION_TO_INSPECT = "LateUpdate"


with open(DECOMPILED_PATH / f"{MODULE_TO_INSPECT}.cs", "r", encoding="utf-8") as f:
    fn_lines = find_function_lines(MODULE_TO_INSPECT, FUNCTION_TO_INSPECT, MODULE_INDEX)
    if len(fn_lines) != 1:
        print("unexpected functions")

    fn_line = fn_lines[0]

    body = get_function_body(MODULE_TO_INSPECT, fn_line, ALL_MODULES)
    for line_no, line in enumerate(body, start=fn_line + 1):
        line = line.lower()
        if "random." in line or "pickrandom" in line:
            print(
                f"{MODULE_TO_INSPECT}.{FUNCTION_TO_INSPECT}.cs:{line_no} {line.strip()}"
            )

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
