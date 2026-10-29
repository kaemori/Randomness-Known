import base64
import gzip
import json
from dataclasses import dataclass
import math

import numpy as np

from tools.pyfastnoiselite_binded import FastNoiseLite
from tools.vectors import Vector2, Vector3
from tools.unity_shim import Mathf, Plaything, make_unity_engine


@dataclass
class RunSettings:
    settings: dict

    def GetRunSettingFloat(self, query):
        return self.settings[query]

    @staticmethod
    def from_preset_str(preset):
        raw = json.loads(gzip.decompress(base64.b64decode(preset)))
        return RunSettings({d["Item1"]: d["Item2"] for d in raw})


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


def generation_settings(
    *, biomeDepth, width, height, chunkWidth, chunkHeight, run_settings, Random
) -> dict:
    return {
        # inputs
        "biomeDepth": biomeDepth,
        "width": width,
        "height": height,
        "chunkWidth": chunkWidth,
        "chunkHeight": chunkHeight,
        "Random": Random,
        "WorldGeneration": run_settings,
        # derived
        "halfWidth": width / 2,
        "halfHeight": height / 2,
        "worldBlocks": np.zeros((width, height), dtype=np.uint16),
        "fluid": np.zeros((width, height), dtype=np.uint8),
        # libs / unity stand-ins
        "UnityEngine": make_unity_engine(Random),
        "math": math,
        "Mathf": Mathf,
        "FastNoiseLite": FastNoiseLite,
        "Vector2Int": Vector2,
        "Vector3Int": Vector3,
        # terrain
        "biomeOverride": float("nan"),
        "OverrideSceneType": Plaything(),
        # hooks
        "SetLoadingText": SetLoadingText,
        "GenerateOres": GenerateOres,
        "UpdateWorld": UpdateWorld,
        "PlaceLiquids": PlaceLiquids,
    }
