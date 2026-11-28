import ast
import json
import pickle

from .generation import Environment
from .unity_random import splitmix64
from .state import WorldState
from .run_settings import DEFAULT_PRESET, RunSettings
from tools.liqfiller import place_liquids


_FUNCTIONS = (
    "GenerateOres",
    "WorldGenerateStructures",
    "GenerateTree",
    "GenerateBigMushroom",
    "GenerateDropCapsules",
    "GenerateCollapsedPods",
    "GenerateLifePods",
)


class _AwaitGenerationCalls(ast.NodeTransformer):
    def __init__(self, names):
        self.names = names

    def visit_Call(self, node):
        node = self.generic_visit(node)
        func = node.func
        should_await = (
            isinstance(func, ast.Name) and func.id in self.names
        ) or (
            isinstance(func, ast.Attribute)
            and func.attr == "noise"
            and isinstance(func.value, ast.Name)
            and func.value.id == "pyglslfnl"
        )
        return ast.copy_location(ast.Await(node), node) if should_await else node


def _async_functions(source, names):
    tree = ast.parse(source)
    transformed = _AwaitGenerationCalls(names).visit(tree)
    async_body = []
    for node in transformed.body:
        if isinstance(node, ast.FunctionDef):
            body = list(node.body)
            if not any(
                isinstance(statement, ast.Global)
                and "xs_state" in statement.names
                for statement in body
            ):
                body.insert(0, ast.Global(names=["xs_state"]))
            node = ast.AsyncFunctionDef(
                name=node.name,
                args=node.args,
                body=body,
                decorator_list=node.decorator_list,
                returns=node.returns,
                type_comment=node.type_comment,
            )
        async_body.append(node)
    transformed.body = async_body
    return ast.fix_missing_locations(transformed)


def _terrain_runner(source, names):
    tree = ast.parse(source.replace("exit()", "return"))
    tree = _AwaitGenerationCalls(names).visit(tree)
    runner = ast.AsyncFunctionDef(
        name="_run_terrain",
        args=ast.arguments(
            posonlyargs=[], args=[], vararg=None, kwonlyargs=[], kw_defaults=[],
            kwarg=None, defaults=[]
        ),
        body=[ast.Global(names=["xs_state"]), *tree.body],
        decorator_list=[],
    )
    module = ast.Module(body=[runner], type_ignores=[])
    return ast.fix_missing_locations(module)


def load_packages(terrain_path="terrgen.pkg", structures_path="structures.pkg"):
    with open(terrain_path, "rb") as package_file:
        terrain = pickle.load(package_file)
    with open(structures_path, "r", encoding="utf-8") as package_file:
        structures = json.load(package_file)
    if terrain.get("format") != "spectra3-terrgen-v1":
        raise ValueError("Unsupported terrain package format")
    if set(terrain.get("layers", ())) != set(range(11)):
        raise ValueError("Terrain package must include every layer from 0 to 10")
    for function_name in _FUNCTIONS:
        if function_name not in terrain.get("Functions", {}):
            raise ValueError(f"Terrain package is missing {function_name}")
        if set(terrain["Functions"][function_name]) != {
            str(layer) for layer in range(11)
        }:
            raise ValueError(f"Terrain package is missing layers for {function_name}")
    if set(terrain.get("WorldGenerateTerrain", {})) != {
        str(layer) for layer in range(11)
    }:
        raise ValueError("Terrain package must contain terrain code for layers 0 to 10")
    if structures.get("format") != "spectra3-structures-v1":
        raise ValueError("Unsupported structure package format")
    terrain["structures"] = structures["structures"]
    return terrain


async def generate_layer(package, layer, width=1024, height=1024, seed="purr"):
    if layer not in package.get("layers", ()):
        raise ValueError(f"Terrain package does not contain layer {layer}")
    settings = RunSettings.from_preset_str(DEFAULT_PRESET)
    world = WorldState.create(
        biome_depth=layer,
        width=width,
        height=height,
        chunk_width=16,
        chunk_height=16,
        run_settings=settings,
        random_state=splitmix64(seed),
    )
    env = Environment(world, package, place_liquids=place_liquids)
    scope = env.as_dict

    def bridge_random(function):
        def call(*args):
            explicit_state = (
                len(args) >= 1
                and isinstance(args[0], (list, tuple))
                and len(args[0]) == 4
            )
            if explicit_state:
                env.xs_state[:] = args[0]
                call_args = args[1:]
            else:
                call_args = args
            env.xs_state[:], value = function(env.xs_state, *call_args)
            scope["xs_state"] = tuple(env.xs_state)
            return (tuple(env.xs_state), value) if explicit_state else value

        return call

    from .unity_random import xs_range_ambig, xs_range_float, xs_range_int, xs_value

    scope.update(
        {
            "xs_value": bridge_random(xs_value),
            "xs_range_ambig": bridge_random(xs_range_ambig),
            "xs_range_float": bridge_random(xs_range_float),
            "xs_range_int": bridge_random(xs_range_int),
        }
    )

    def tracked_try_generate_specific(*args, **kwargs):
        result = env.try_generate_specific(*args, **kwargs)
        scope["xs_state"] = tuple(env.xs_state)
        return result

    scope["try_generate_specific"] = tracked_try_generate_specific
    generate_block_circle = env.GenerateBlockCircle

    def tracked_generate_block_circle(*args, **kwargs):
        result = generate_block_circle(*args, **kwargs)
        scope["xs_state"] = tuple(env.xs_state)
        return result

    scope["GenerateBlockCircle"] = tracked_generate_block_circle
    if env.PlaceLiquids is not None:
        place_liquids_call = env.PlaceLiquids

        def tracked_place_liquids(*args, **kwargs):
            result = place_liquids_call(*args, **kwargs)
            scope["xs_state"] = tuple(env.xs_state)
            return result

        scope["PlaceLiquids"] = tracked_place_liquids

    sources = {
        name: package["Functions"][name][str(layer)]
        for name in _FUNCTIONS
    }
    for name in _FUNCTIONS:
        source = sources[name].replace("exit()", "return")
        tree = _async_functions(source, set(_FUNCTIONS))
        exec(compile(tree, f"<{name}:{layer}>", "exec"), scope)

    terrain_source = package["WorldGenerateTerrain"][str(layer)]
    runner_tree = _terrain_runner(terrain_source, set(_FUNCTIONS))
    exec(compile(runner_tree, f"<WorldGenerateTerrain:{layer}>", "exec"), scope)
    await scope["_run_terrain"]()
    return world


def world_summary(world):
    blocks = world.world_blocks
    solid = int(((blocks > 0) & (blocks <= 42)).sum())
    liquid = int((blocks >= 43).sum())
    return {
        "width": world.width,
        "height": world.height,
        "layer": world.biome_depth,
        "solidTiles": solid,
        "liquidTiles": liquid,
        "entities": len(world.world_entities),
    }
