from pathlib import Path
from dataclasses import dataclass, make_dataclass
import shutil
import regex as re

from helpers.csharp_syntax import find_calls_in_lines, is_line_function
from helpers.function_getter import (
    EntryPoint,
    get_function_body,
    load_modules,
    load_module_index,
)
from tools.index_cache import cache_output
from cparser.transpiler import transpile

DECOMPILED_PATH = Path(__file__).parent / "Assembly-CSharp"
ALL_MODULES = cache_output(load_modules, DECOMPILED_PATH)
MODULE_INDEX = cache_output(load_module_index, ALL_MODULES)

# holy shit device name leak??
ICON_PATH = Path("/home/fern/casualties_unknown_assets/Assets/Texture2D")
HARDCODED_PATH = Path().cwd() / "tools" / "hardcodedimages"


# grab block ref
def get_blockinfo(all_modules, module_index):
    entry = EntryPoint("WorldGeneration", "GetBlockInfo")
    entry_line = entry.resolve(module_index)

    blocks = {}
    pending_case = None
    lines_to_skip = 0

    function_body = get_function_body(entry.module, entry_line, all_modules)
    for line in function_body:
        line = line.strip()

        if lines_to_skip > 0:
            lines_to_skip -= 1
            continue

        if "case" in line:
            pending_case = int(line.split("case")[1].split(":")[0].strip())
            lines_to_skip = 2
        elif pending_case is not None:
            name = line.split('("')[1].split('")')[0]
            blocks[pending_case] = name
            pending_case = None

    # {0: 'air', 1: 'lightrock', 2: 'gravel', 3: 'scrappile', 4: 'trashpile', 5: 'concretetile', 6: 'steeltile', 7: 'glass', 8: 'rubber', 9: 'plastic', 10: 'heatresistantalloy', 11: 'wood', 12: 'sand', 13: 'sandstone', 14: 'infinirock', 15: 'clay', 16: 'soil', 17: 'granite', 18: 'marble',19: 'limestone', 20: 'bricks', 21: 'scaffolding', 22: 'toxirock', 23: 'grass', 24: 'log', 25: 'leaves', 26: 'snow', 27: 'ice', 28: 'thinice', 29: 'powdersnow', 30: 'heavyrock', 31: 'fungus', 32: 'mushroombody', 33: 'mushroomcap', 34: 'copper', 35: 'ilmenite'}
    return blocks


def copy_icon_images_to_hardcoded_path(block_info):
    block_name = block_info.values()
    exceptions = {
        "lightrock": "rock",
        "scrappile": "scrap",
        "trashpile": "trash",
        "concretetile": "concrete",
        "steeltile": "steelplate",
    }
    exceptions = {value: key for key, value in exceptions.items()}
    HARDCODED_PATH.mkdir(parents=True, exist_ok=True)
    hardcoded = {"gravel.png", "infinirock.png"}
    for image_path in ICON_PATH.glob("*.png"):
        stem = exceptions.get(image_path.stem, image_path.stem)
        if stem in block_name and image_path.name not in hardcoded:
            shutil.copy2(
                image_path,
                HARDCODED_PATH / (stem + image_path.suffix),
            )


def get_id_color_mapping(block_info):
    from PIL import Image

    def _avg_color(image_path):
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            pixels = list(img.get_flattened_data())
            num_pixels = len(pixels)
            avg_color = tuple(sum(channel) // num_pixels for channel in zip(*pixels))
            return avg_color

    id_color_mapping = {"air": (20, 20, 35)}
    for block_id, block_name in block_info.items():
        if block_name in id_color_mapping:
            continue
        try:
            id_color_mapping[block_id] = _avg_color(
                HARDCODED_PATH / f"{block_name}.png"
            )
        except Exception as e:
            print(f"failed to get {block_name}")
            raise e

    return id_color_mapping


def get_id_image_mapping(block_info):
    import matplotlib.image as mpimg
    from PIL import Image

    air_img = Image.new("RGB", (8, 8), (20, 20, 35))

    id_color_mapping = {"air": air_img}
    for block_id, block_name in block_info.items():
        if block_name in id_color_mapping:
            continue
        try:
            with Image.open(HARDCODED_PATH / f"{block_name}.png") as img:
                img = img.convert("RGB")
                img = img.resize((8, 8), Image.BILINEAR)
                id_color_mapping[block_id] = img

        except Exception as e:
            print(f"failed to get {block_name}")
            raise e

    return id_color_mapping


# blocks = get_blockinfo(ALL_MODULES, MODULE_INDEX)
# copy_icon_images_to_hardcoded_path(blocks)


def _normalize_addone(func):
    addone = re.compile(r"^((?:\s{4})*)(\w*) = (\w*);\n\1\3 = \2 \+ 1;", re.MULTILINE)
    return (
        re.sub(addone, r"\1\3++;", "".join(func))
        .replace("int num2;\n", "")
        .splitlines(keepends=True)
    )


def clean_up_function(function):
    while_loop = re.compile(
        r"^((?:\s{4})*)(?:\S)*\s*(\S*)\s*=\s*0;\n"
        r"(?>^(?:\s{4})*while[^<]*\< .*?([^()]+)\)+$)\n"
        r"^(?:\s{4})*\{\n"
        r"((?:\n|.)*?)\n"
        r"^\1\s{4}\2\+\+;\n",
        re.MULTILINE,
    )

    function = [line.replace("\t", "    ")[4:] for line in function]
    function = _normalize_addone(function)
    function_body_str = "".join(function)
    last_function_body_str = None
    while last_function_body_str != function_body_str:
        last_function_body_str = function_body_str
        function_body_str = re.sub(
            while_loop,
            r"\1for (int \2 = 0; \2 < \3; \2++)\n\1{\n\4\n",
            function_body_str,
        )

    return function_body_str.splitlines(keepends=True)


if __name__ == "__main__":
    # with open("terr_ir.cs", "w") as ir:
    #     entry = EntryPoint("WorldGeneration", "WorldGenerateTerrain")
    #     entry_line = entry.resolve(MODULE_INDEX)

    #     function_body = get_function_body(entry.module, entry_line, ALL_MODULES)
    #     function_body = clean_up_function(function_body)
    #     ir.writelines(function_body)
    with open("gen_ores.cs", "w") as ir:
        entry = EntryPoint("WorldGeneration", "GenerateOres")
        entry_line = entry.resolve(MODULE_INDEX)

        function_body = get_function_body(entry.module, entry_line, ALL_MODULES)
        function_body = clean_up_function(function_body)
        ir.writelines(function_body)
