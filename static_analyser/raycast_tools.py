from dataclasses import dataclass
from typing import Callable, Optional, Tuple
import numpy as np

from worldgen import GenerationSettings

Vec2 = Tuple[float, float]


def default_is_solid(block_id):
    return block_id != 0


@dataclass
class Raycaster:
    gensettings: GenerationSettings

    @property
    def _blocks(self):
        return self.gensettings.worldBlocks.T

    def _cast_down(self, col, start_row, max_distance, is_solid):
        blocks = self._blocks
        height = blocks.shape[0]
        end_row = min(start_row + max_distance, height)
        strip = blocks[start_row:end_row, col]
        solid_mask = np.frompyfunc(is_solid, 1, 1)(strip).astype(bool)
        hits = np.nonzero(solid_mask)[0]
        if not hits.size:
            return None
        rel = hits[0]
        hit_row = start_row + rel
        return (float(col), float(hit_row)), float(rel), (hit_row, col)

    def _cast_up(self, col, start_row, max_distance, is_solid):
        blocks = self._blocks
        end_row = max(start_row - max_distance, 0)
        strip = blocks[end_row:start_row, col][::-1]
        solid_mask = np.frompyfunc(is_solid, 1, 1)(strip).astype(bool)
        hits = np.nonzero(solid_mask)[0]
        if not hits.size:
            return None
        rel = hits[0]
        hit_row = start_row - rel
        return (float(col), float(hit_row)), float(rel), (hit_row, col)

    def _cast_right(self, row, start_col, max_distance, is_solid):
        blocks = self._blocks
        width = blocks.shape[1]
        end_col = min(start_col + max_distance, width)
        strip = blocks[row, start_col:end_col]
        solid_mask = np.frompyfunc(is_solid, 1, 1)(strip).astype(bool)
        hits = np.nonzero(solid_mask)[0]
        if not hits.size:
            return None
        rel = hits[0]
        hit_col = start_col + rel
        return (float(hit_col), float(row)), float(rel), (row, hit_col)

    def _cast_left(self, row, start_col, max_distance, is_solid):
        blocks = self._blocks
        end_col = max(start_col - max_distance, 0)
        strip = blocks[row, end_col:start_col][::-1]
        solid_mask = np.frompyfunc(is_solid, 1, 1)(strip).astype(bool)
        hits = np.nonzero(solid_mask)[0]
        if not hits.size:
            return None
        rel = hits[0]
        hit_col = start_col - rel
        return (float(hit_col), float(row)), float(rel), (row, hit_col)

    def raycast(self, origin, direction, max_distance, is_solid=default_is_solid):
        blocks = self._blocks
        height, width = blocks.shape
        dx, dy = direction
        length = (dx * dx + dy * dy) ** 0.5
        if length == 0.0:
            return None
        dx, dy = dx / length, dy / length
        AXIS_EPS = 1e-09
        x, y = origin
        col = int(np.floor(x))
        row = int(np.floor(y))
        imax = int(np.ceil(max_distance)) + 1
        if abs(dx) < AXIS_EPS and dy > 0:
            return self._cast_down(col, row, imax, is_solid)
        if abs(dx) < AXIS_EPS and dy < 0:
            return self._cast_up(col, row, imax, is_solid)
        if abs(dy) < AXIS_EPS and dx > 0:
            return self._cast_right(row, col, imax, is_solid)
        if abs(dy) < AXIS_EPS and dx < 0:
            return self._cast_left(row, col, imax, is_solid)
        step_x = 1 if dx > 0 else -1
        step_y = 1 if dy > 0 else -1
        t_delta_x = abs(1.0 / dx) if dx != 0 else float("inf")
        t_delta_y = abs(1.0 / dy) if dy != 0 else float("inf")
        t_max_x = (col + 1 - x) * t_delta_x if dx > 0 else (x - col) * t_delta_x
        t_max_y = (row + 1 - y) * t_delta_y if dy > 0 else (y - row) * t_delta_y
        t = 0.0
        while t <= max_distance:
            if 0 <= row < height and 0 <= col < width:
                if is_solid(int(blocks[row, col])):
                    hit_x = x + dx * t
                    hit_y = y + dy * t
                    return (hit_x, hit_y), t, (row, col)
            else:
                return None
            if t_max_x < t_max_y:
                t = t_max_x
                t_max_x += t_delta_x
                col += step_x
            else:
                t = t_max_y
                t_max_y += t_delta_y
                row += step_y
        return None

    # def raycast_down(self, origin, max_distance=4e2, is_solid=default_is_solid):
    #     return self.raycast(origin, (0.0, 1.0), max_distance, is_solid)

    # def raycast_up(self, origin, max_distance=4e2, is_solid=default_is_solid):
    #     return self.raycast(origin, (0.0, -1.0), max_distance, is_solid)

    # def raycast_right(self, origin, max_distance=4e2, is_solid=default_is_solid):
    #     return self.raycast(origin, (1.0, 0.0), max_distance, is_solid)

    # def raycast_left(self, origin, max_distance=4e2, is_solid=default_is_solid):
    #     return self.raycast(origin, (-1.0, 0.0), max_distance, is_solid)
