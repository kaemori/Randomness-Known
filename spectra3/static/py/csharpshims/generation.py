import math
import random

import numpy as np

from .state import WorldEntity
from .unity import Math, Mathf, Plaything, RandomShim, make_unity_engine
from .vectors import Vector2, Vector3
from .fast_noise_lite import FastNoiseLite
from .unity_random import xs_range_ambig, xs_range_float, xs_range_int, xs_value


def _position(value):
    if hasattr(value, "position"):
        value = value.position
    if hasattr(value, "x") and hasattr(value, "y"):
        return float(value.x), float(value.y)
    return float(value[0]), float(value[1])


def _rotation(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if hasattr(value, "z"):
        return float(value.z)
    if hasattr(value, "rotation"):
        return float(value.rotation)
    return 0.0


def utils_create(env, assetpath, position_or_transform, rotation=0.0):
    if not isinstance(assetpath, str) or not assetpath:
        raise ValueError("entity asset path must be a non-empty string")
    position = _position(position_or_transform)
    flipped = False
    scale = getattr(position_or_transform, "scale", None)
    if scale is not None:
        flipped = getattr(scale, "x", 1) < 0
    entity = WorldEntity(assetpath, position, _rotation(rotation), flipped)
    env.world_entities.append(entity)
    return Plaything()


def _raycast_down(env, origin, distance):
    ox, oy = _position(origin)
    x = int(math.floor(ox + env.halfWidth))
    y = int(math.floor(oy + env.halfHeight))
    if not (0 <= x < env.width and 0 <= y < env.height):
        return None
    end_y = max(0, int(math.floor(y - max(0.0, distance))))
    for cell_y in range(y, end_y - 1, -1):
        block = int(env.worldBlocks[x, cell_y])
        if 1 <= block <= 42:
            return Plaything(
                Vector2(x - env.halfWidth, cell_y - env.halfHeight)
            )
    return None


class _Physics2D:
    def __init__(self, env):
        self._env = env

    def Raycast(self, origin, direction, distance, layer_mask=None):
        if direction.y >= 0 or direction.x != 0:
            raise NotImplementedError("generation currently supports downward raycasts")
        return _raycast_down(self._env, origin, distance)


def _draw_circle(env, pos, tile_id, radius, chance=1.0):
    if not 0 <= int(tile_id) <= 42:
        raise ValueError(f"solid tile ID out of range: {tile_id}")
    cx, cy = int(pos.x), int(pos.y)
    radius = max(0, int(radius))
    for x in range(max(0, cx - radius), min(env.width, cx + radius + 1)):
        for y in range(max(0, cy - radius), min(env.height, cy + radius + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= radius**2:
                if chance >= 1 or _next_random(env, xs_value) < chance:
                    env.worldBlocks[x, y] = tile_id


def _next_random(env, random_fn, *args):
    env.xs_state[:], value = random_fn(env.xs_state, *args)
    return value


class Environment:
    def __init__(self, world_state, package=None, place_liquids=None):
        from gpu_fnl import pyglslfnl

        self._state = world_state
        self._package = package or {}
        self.biomeDepth = world_state.biome_depth
        self.width = world_state.width
        self.height = world_state.height
        self.chunkWidth = world_state.chunk_width
        self.chunkHeight = world_state.chunk_height
        self.halfWidth = world_state.half_width
        self.halfHeight = world_state.half_height
        self.worldBlocks = world_state.world_blocks
        self.world_entities = world_state.world_entities
        self.worldBuildingEntities = self.world_entities
        self.fluid = world_state.world_blocks
        self.xs_state = world_state.random_state
        self.xs_value = xs_value
        self.xs_range_ambig = xs_range_ambig
        self.xs_range_float = xs_range_float
        self.xs_range_int = xs_range_int
        self.Random = RandomShim(
            self.xs_state, xs_range_ambig, xs_range_float, xs_range_int
        )
        self.UnityEngine = make_unity_engine(self.Random)
        self.Vector2 = self.Vector2Int = Vector2
        self.Vector3Int = Vector3
        self.Math = Math
        self.Mathf = Mathf
        self.math = math
        self.np = np
        self.random_choice = random.choice
        self.FastNoiseLite = FastNoiseLite
        self.pyglslfnl = pyglslfnl
        self.WorldGeneration = world_state.run_settings
        self.GetRunSettingFloat = world_state.run_settings.GetRunSettingFloat
        self.biomeOverride = world_state.biome_override
        self.OverrideSceneType = world_state.override_scene_type
        self.fillnet = self.fillstart = self.fillorder = self.groundy = None
        self.Physics2D = _Physics2D(self)
        self.LayerMask = Plaything()
        self.utils_create = lambda *args, **kwargs: utils_create(
            self, *args, **kwargs
        )
        self.GenerateBlockCircle = lambda pos, tile_id, radius, *_: _draw_circle(
            self, pos, tile_id, radius
        )
        self.SimpleBlockCircle = lambda pos, radius, tile_id: _draw_circle(
            self, pos, tile_id, radius
        )
        self.DrawLine = self._draw_line
        self.DrawEmptyLine = lambda a, b, thickness: self._draw_line(
            a, b, thickness, 0
        )
        self.WorldToBlockPos = lambda pos: Vector2(
            pos.x + self.halfWidth, pos.y + self.halfHeight
        )
        self.BlockToWorldPos = lambda pos: Vector2(
            pos.x - self.halfWidth - 0.5, pos.y - self.halfHeight - 0.5
        )
        self.try_generate_specific = lambda *args, **kwargs: try_generate_specific(
            self, *args, **kwargs
        )
        self.SetLoadingText = lambda word: None
        self.PlaceLiquids = (
            (lambda *args, **kwargs: place_liquids(self, *args, **kwargs))
            if place_liquids is not None
            else None
        )
        self.as_dict = {
            key: value
            for key, value in vars(self).items()
            if not key.startswith("_")
        }
        self.as_dict.update(
            {
                "worldBuildingEntities": self.world_entities,
                "worldBlocks": self.worldBlocks,
                "worldEntities": self.world_entities,
            }
        )

    def _draw_line(self, a, b, thickness, tile_id):
        x0, y0 = int(a.x), int(a.y)
        x1, y1 = int(b.x), int(b.y)
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        radius = max(0, int(thickness) // 2)
        for step in range(steps + 1):
            x = round(x0 + (x1 - x0) * step / steps)
            y = round(y0 + (y1 - y0) * step / steps)
            _draw_circle(self, Vector2(x, y), tile_id, radius)


def try_generate_specific(
    env,
    attempts,
    resource_path,
    block_chance,
    gen_mode,
    *,
    ground=False,
    entity=False,
    child_index=None,
    circles=(),
):
    template = env._package.get("structures", {}).get(resource_path)
    count = math.ceil(max(0, attempts))
    placed = 0
    for _ in range(count):
        if _next_random(env, xs_value) > block_chance:
            continue
        x = _next_random(env, xs_range_int, 0, env.width)
        y = _next_random(env, xs_range_int, 0, env.height)
        position = Vector2(x, y)
        if ground:
            hit = _raycast_down(
                env, Vector2(x - env.halfWidth, y - env.halfHeight), env.height
            )
            if hit is None:
                continue
            position = env.WorldToBlockPos(hit.point)
        for circle in circles:
            tile_id, radius = int(circle[0]), int(circle[1])
            chance = float(circle[2]) if len(circle) > 2 else 1.0
            _draw_circle(env, position, tile_id, radius, chance)
        if template is not None:
            _place_template(env, template, position, bool(entity))
            if entity and not template.get("entities"):
                utils_create(env, resource_path, env.BlockToWorldPos(position))
        elif entity:
            utils_create(env, resource_path, env.BlockToWorldPos(position))
        placed += 1
    return placed


def _place_template(env, template, origin, include_entities):
    for tilemap in template.get("tilemaps", ()):
        for x, y, tile_id in tilemap.get("tiles", ()):
            tile_id = int(tile_id)
            if not 0 <= tile_id <= 42:
                raise ValueError(f"structure solid tile ID out of range: {tile_id}")
            target_x = int(origin.x) + int(x)
            target_y = int(origin.y) + int(y)
            if 0 <= target_x < env.width and 0 <= target_y < env.height:
                env.worldBlocks[target_x, target_y] = tile_id
    if include_entities:
        world_origin = env.BlockToWorldPos(origin)
        for entry in template.get("entities", ()):
            pos = entry["position"]
            assetpath = entry.get("assetpath") or entry.get("id") or entry.get("name")
            env.world_entities.append(
                WorldEntity(
                    assetpath,
                    (world_origin.x + float(pos["x"]), world_origin.y + float(pos["y"])),
                    float(entry.get("rotation_deg", 0.0)),
                    float(entry.get("scale", {}).get("x", 1.0)) < 0,
                )
            )
