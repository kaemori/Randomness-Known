from dataclasses import dataclass
import math

import numpy as np

from tools.unity_shim import Plaything
from tools.unity_random import xs_value, xs_range_ambig, xs_range_float, xs_range_int


@dataclass(slots=True)
class WorldState:
    biome_depth: int
    width: int
    height: int
    chunk_width: int
    chunk_height: int
    run_settings: object
    random_state: list
    world_blocks: np.ndarray
    fluid: np.ndarray
    biome_override: float
    override_scene_type: object

    def __post_init__(self):
        if self.biome_depth == 0:
            _rd = self.random_state
            for _ in range(412):
                xs_value(_rd)

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
        random_state
    ):
        return cls(
            biome_depth=biome_depth,
            width=width,
            height=height,
            chunk_width=chunk_width,
            chunk_height=chunk_height,
            run_settings=run_settings,
            random_state=random_state,
            world_blocks=np.zeros((width, height), dtype=np.uint16),
            fluid=np.zeros((width, height), dtype=np.uint8),
            # biome_override=float("nan"),
            # biome_override='"theliteralNone"',
            biome_override=None,
            override_scene_type=Plaything(),
        )

    @property
    def half_width(self):
        return self.width / 2

    @property
    def half_height(self):
        return self.height / 2
