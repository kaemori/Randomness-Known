from pathlib import Path
import shutil
import regex as re

from cparser.csfunc import getfunc

ICON_PATH = Path().cwd() / "casproject" / "Assets" / "Texture2D"
HARDCODED_PATH = Path().cwd() / "spectra_resources"
HARDCODED_ENTITY_PATH = Path().cwd() / "spectra_resources" / "entities"


def get_blockinfo():
    blocks = {}
    curr_id = None

    function_body = getfunc("WorldGeneration", "GetBlockInfo")
    for line in function_body.splitlines():
        line = line.strip()
        if "=>" in line and "null" not in line:
            curr_id = int(line.split("=>")[0].strip())
        if "Locale.GetOther" in line:
            blocks[curr_id] = line.split('("')[1].split('")')[0]
    # {0: 'air', 1: 'lightrock', 2: 'gravel', 3: 'scrappile', 4: 'trashpile', 5: 'concretetile', 6: 'steeltile', 7: 'glass', 8: 'rubber', 9: 'plastic', 10: 'heatresistantalloy', 11: 'wood', 12: 'sand', 13: 'sandstone', 14: 'infinirock', 15: 'clay', 16: 'soil', 17: 'granite', 18: 'marble', 19: 'limestone', 20: 'bricks', 21: 'scaffolding', 22: 'toxirock', 23: 'grass', 24: 'log', 25: 'leaves', 26: 'snow', 27: 'ice', 28: 'thinice', 29: 'powdersnow', 30: 'heavyrock', 31: 'fungus', 32: 'mushroombody', 33: 'mushroomcap', 34: 'copper', 35: 'ilmenite'}
    return blocks


ASSET_BLOCK_NAME_ALIASES = {
    "dirt": "gravel",
    "rock": "lightrock",
    "scrap": "scrappile",
    "trash": "trashpile",
    "concrete": "concretetile",
    "steelplate": "steeltile",
    "infinirock": "infinirock",
    "specialnulltile": "air",
}


def get_guid_to_blockid(resources_path, block_info):
    block_ids = {name: block_id for block_id, name in block_info.items()}
    guid_to_blockid = {"null": block_ids["gravel"], "-1": 0}

    for meta_path in Path(resources_path).glob("*.asset.meta"):
        asset_name = meta_path.name.removesuffix(".asset.meta").lower()
        block_name = ASSET_BLOCK_NAME_ALIASES.get(asset_name, asset_name)
        if block_name not in block_ids:
            continue

        guid = None
        for line in meta_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("guid:"):
                guid = line.partition(":")[2].strip()
                break
        if guid is None:
            raise ValueError(f"Missing GUID in {meta_path}")
        guid_to_blockid[guid] = block_ids[block_name]

    return guid_to_blockid


def copy_icon_images(block_info):
    block_name = block_info.values()
    exceptions = {
        "gravel": "dirt",
        "lightrock": "rock",
        "scrappile": "scrap",
        "trashpile": "trash",
        "concretetile": "concrete",
        "steeltile": "steelplate",
        "infinirock": "indestructirock",
    }
    exceptions = {value: key for key, value in exceptions.items()}
    HARDCODED_PATH.mkdir(parents=True, exist_ok=True)
    for image_path in ICON_PATH.glob("*.png"):
        stem = exceptions.get(image_path.stem, image_path.stem)
        if stem in block_name:
            shutil.copy2(
                image_path,
                HARDCODED_PATH / (stem + image_path.suffix),
            )


def copy_entity_images():
    items = (
        {
            "LifePodLight",
            "beartrap",
            "containercrate",
            "bioterminal",
            "dropcapsule",
            "rechargingstation",
            "brownshroom",
            "foodbox",
            "medcrate",
            "sawblade",
            "scrapeater",
            "ladder",
            "reinforceddoor",
        }
        | {
            "lifepodchest",
            "lifepodpump",
            "LifePodLight",
            "lifepodheater",
            "lifepodbuttonshower",
            "lifepodshower",
            "lifepodbuttonheat",
            "LoreNote",
            "epda",
            "manualdefibrillator",
            "defibrack",
            "aed",
        }
        | {"experimentflesh", "internalorgans"}
        | {"debug_cross"}
    )
    exceptions = {
        "foodbox": "foodcrate",
        "reinforceddoor": "door",
        "lifepodbuttonshower": "podbutton",
        "lifepodbuttonheat": "podbutton",
        "LifePodLight": "lightcircle",
        "LoreNote": "wallpaper",
        "debug_cross": "radpos",
    }
    HARDCODED_ENTITY_PATH.mkdir(parents=True, exist_ok=True)

    for item in items:
        file = exceptions.get(item, item)
        try:
            iconpath = [
                i for i in ICON_PATH.glob(f"{file}.*") if not i.name.endswith(".meta")
            ][0]
            shutil.copy2(iconpath, HARDCODED_ENTITY_PATH / (item + iconpath.suffix))
        except:
            print(f"{item} not exist")

    # for image_path in ICON_PATH.glob("*.png"):
    #     print(exceptions.get(image_path.stem, image_path.stem))


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


def get_id_image_mapping(block_info, alpha_pixel_blend_to=(20, 20, 35)):
    from PIL import Image

    air_img = Image.new("RGB", (8, 8), (20, 20, 35))
    id_color_mapping = {"air": air_img}

    bg = Image.new("RGBA", (8, 8), alpha_pixel_blend_to + (255,))

    def find_clearest_8x8(img):
        w, h = img.size
        if w < 8 or h < 8:
            return (0, 0, w, h)

        alpha = img.getchannel("A")
        best_box = (0, 0, 8, 8)
        best_transparent_count = None

        # topright to bottomleft
        perfect_boxes = []
        for top in range(h - 8 + 1):
            for left in range(w - 8, -1, -1):
                region = alpha.crop((left, top, left + 8, top + 8))
                transparent_count = sum(1 for p in region.getdata() if p == 0)

                if transparent_count == 0:
                    perfect_boxes.append((left, top, left + 8, top + 8))

                if (
                    best_transparent_count is None
                    or transparent_count < best_transparent_count
                ):
                    best_transparent_count = transparent_count
                    best_box = (left, top, left + 8, top + 8)

        if len(perfect_boxes) == 0:
            return best_box
        else:
            # give the perfect box closest to the center
            center_pbox = [
                (x1, y1, x2, y2)
                for x1, y1, x2, y2 in perfect_boxes
                if x1 == y1 and x2 == y2
            ]
            if len(center_pbox) != 0:
                return center_pbox[0]
            else:
                perfect_boxes[0]

    for block_id, block_name in block_info.items():
        if block_name in id_color_mapping:
            continue
        try:
            with Image.open(HARDCODED_PATH / f"{block_name}.png") as img:
                img = img.convert("RGBA")

                if img.size != (8, 8):
                    box = find_clearest_8x8(img)
                    img = img.crop(box)

                img = img.resize((8, 8), Image.BILINEAR)

                composited = Image.alpha_composite(bg, img)
                id_color_mapping[block_id] = composited.convert("RGB")

        except Exception as e:
            print(f"failed to get {block_name}")
            raise e

    return id_color_mapping


# blocks = get_blockinfo(ALL_MODULES, MODULE_INDEX)
# copy_icon_images(blocks)


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
    pass
    # all_modules = cache_output(load_modules, Path(__file__).parent / "Assembly-CSharp")
    # module_index = cache_output(load_module_index, all_modules)
    # copy_icon_images(get_blockinfo(all_modules, module_index))
    # copy_entity_images()

    # all_modules = load_modules(Path(__file__).parent / "Assembly-CSharp")
    # module_index = load_module_index(all_modules)

    # # with open("terr_ir.cs", "w") as ir:
    # #     entry = EntryPoint("WorldGeneration", "WorldGenerateTerrain")
    # #     entry_line = entry.resolve(MODULE_INDEX)

    # #     function_body = get_function_body(entry.module, entry_line, ALL_MODULES)
    # #     function_body = clean_up_function(function_body)
    # #     ir.writelines(function_body)
    # with open("gen_ores.cs", "w") as ir:
    #     entry = EntryPoint("WorldGeneration", "GenerateOres")
    #     entry_line = entry.resolve(module_index)

    #     function_body = get_function_body(entry.module, entry_line, all_modules)
    #     function_body = clean_up_function(function_body)
    #     ir.writelines(function_body)
