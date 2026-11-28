from dataclasses import dataclass, field

import numpy as np
from .unity_random import xs_value


@dataclass(slots=True)
class WorldEntity:
    assetpath: str
    position: tuple[float, float]
    rotation: float = 0.0
    is_flipped: bool = False

    def __post_init__(self):
        if not isinstance(self.assetpath, str) or not self.assetpath:
            raise ValueError("entity asset path must be a non-empty string")
        if len(self.position) != 2:
            raise ValueError("entity position must contain two coordinates")

    def to_dict(self):
        return {
            "assetpath": self.assetpath,
            "transform": {
                "position": [float(self.position[0]), float(self.position[1])],
                "rotation": float(self.rotation) % 360.0,
                "isFlipped": bool(self.is_flipped),
            },
        }


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
    world_entities: list = field(default_factory=list)
    biome_override: object = None
    override_scene_type: object = None

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
        random_state,
        world_blocks=None,
    ):
        if width <= 0 or height <= 0:
            raise ValueError("world dimensions must be positive")
        if not 0 <= biome_depth <= 10:
            raise ValueError("biome depth must be between 0 and 10")
        if run_settings is None:
            raise ValueError("run settings are required")
        if random_state is None:
            raise ValueError("random state is required")
        blocks = (
            np.zeros((width, height), dtype=np.uint16)
            if world_blocks is None
            else np.asarray(world_blocks)
        )
        if blocks.shape != (width, height):
            raise ValueError(
                f"world blocks have shape {blocks.shape}, expected {(width, height)}"
            )
        if not np.issubdtype(blocks.dtype, np.integer):
            raise TypeError("world block IDs must use an integer array")
        if np.any(blocks < 0):
            raise ValueError("world block IDs cannot be negative")
        if np.any(blocks > 65535):
            raise ValueError("world block IDs must fit in an unsigned 16-bit value")
        if blocks.dtype.itemsize < 2:
            blocks = blocks.astype(np.uint16)
        if biome_depth == 0:
            for _ in range(412):
                random_state[:], _ = xs_value(random_state)
        return cls(
            biome_depth=biome_depth,
            width=width,
            height=height,
            chunk_width=chunk_width,
            chunk_height=chunk_height,
            run_settings=run_settings,
            random_state=random_state,
            world_blocks=blocks,
        )

    @property
    def world_buildingentities(self):
        return self.world_entities

    @property
    def worldblocks(self):
        return self.world_blocks

    @property
    def worldentities(self):
        return self.world_entities

    @property
    def fluid(self):
        return self.world_blocks

    @property
    def half_width(self):
        return self.width / 2

    @property
    def half_height(self):
        return self.height / 2

    def to_dict(self):
        return {
            "worldblocks": self.world_blocks.tolist(),
            "worldentities": [
                entity.to_dict() if isinstance(entity, WorldEntity) else entity
                for entity in self.world_entities
            ],
        }
