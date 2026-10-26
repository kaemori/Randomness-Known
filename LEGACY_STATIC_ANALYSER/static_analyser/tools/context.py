from dataclasses import dataclass
from pathlib import Path
from helpers.transpiler import FunctionTranspiler


@dataclass
class WorldgenContext:
    worldgen_module: str
    decompiled_path: Path
    all_modules: dict
    module_index: dict
    blockinfo: dict
    transpiler: FunctionTranspiler
