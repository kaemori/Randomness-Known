import math

from tools.pyfastnoiselite_binded import FastNoiseLite
from tools.unity_shim import Mathf, Plaything, make_unity_engine
from tools.vectors import Vector2, Vector3


def SetLoadingText(word):
    print(f"SLT: {word}")


def GenerateOres():
    print("generate ores!")
    return Plaything()


def UpdateWorld():
    print("update world!")
    return Plaything()


def PlaceLiquids(perchunk, type, maxfill):
    print("PlaceLiquids")
    return Plaything()


def build_environment(world_state):
    return {
        "biomeDepth": world_state.biome_depth,
        "width": world_state.width,
        "height": world_state.height,
        "chunkWidth": world_state.chunk_width,
        "chunkHeight": world_state.chunk_height,
        "Random": world_state.random,
        "WorldGeneration": world_state.run_settings,
        "halfWidth": world_state.half_width,
        "halfHeight": world_state.half_height,
        "worldBlocks": world_state.world_blocks,
        "fluid": world_state.fluid,
        "UnityEngine": make_unity_engine(world_state.random),
        "math": math,
        "Mathf": Mathf,
        "FastNoiseLite": FastNoiseLite,
        "Vector2Int": Vector2,
        "Vector3Int": Vector3,
        "biomeOverride": world_state.biome_override,
        "OverrideSceneType": world_state.override_scene_type,
        "SetLoadingText": SetLoadingText,
        "GenerateOres": GenerateOres,
        "UpdateWorld": UpdateWorld,
        "PlaceLiquids": PlaceLiquids,
    }
