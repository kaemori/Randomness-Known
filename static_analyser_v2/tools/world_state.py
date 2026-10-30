from dataclasses import dataclass
import math

import numpy as np

from tools.unity_shim import Plaything


@dataclass(slots=True)
class WorldState:
    biome_depth: int
    width: int
    height: int
    chunk_width: int
    chunk_height: int
    run_settings: object
    random: object
    world_blocks: np.ndarray
    fluid: np.ndarray
    biome_override: float
    override_scene_type: object

    @classmethod
    def create(
        cls,
        *,
        biome_depth,
        width,
        height,
        chunk_width,
        chunk_height,
        run_settings,
        random
    ):
        return cls(
            biome_depth=biome_depth,
            width=width,
            height=height,
            chunk_width=chunk_width,
            chunk_height=chunk_height,
            run_settings=run_settings,
            random=random,
            world_blocks=np.zeros((width, height), dtype=np.uint16),
            fluid=np.zeros((width, height), dtype=np.uint8),
            biome_override=float("nan"),
            override_scene_type=Plaything(),
        )

    @property
    def half_width(self):
        return self.width / 2

    @property
    def half_height(self):
        return self.height / 2
