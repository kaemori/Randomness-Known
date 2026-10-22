from __future__ import annotations
import tkinter as tk
from tkinter import ttk
import numpy as np
import math
from PIL import Image, ImageTk

to_rgb = lambda x: tuple(int(x[i : i + 2], 16) for i in (0, 2, 4))
FLUID_COLORS = {1: to_rgb("223355"), 2: to_rgb("224400")}
FLUID_ALPHA = 0.45
BACKGROUND_COLOR = np.array((20, 20, 35), dtype=np.uint8)


def _build_color_lut(id_color_mapping, max_id):
    lut = np.zeros((max_id + 1, 3), dtype=np.uint8)
    for block_id, color in id_color_mapping.items():
        if isinstance(block_id, int) and 0 <= block_id <= max_id:
            lut[block_id] = color
    return lut


def _build_tile_atlas(id_image_mapping, max_id, tile_size):
    atlas = np.zeros((max_id + 1, tile_size, tile_size, 3), dtype=np.uint8)
    for block_id, tile_img in id_image_mapping.items():
        if isinstance(block_id, int) and 0 <= block_id <= max_id:
            img = tile_img.convert("RGB")
            if img.size != (tile_size, tile_size):
                img = img.resize((tile_size, tile_size), Image.NEAREST)
            atlas[block_id] = np.asarray(img)
    return atlas


def _fluid_lut(max_fluid_id):
    lut = np.zeros((max(max_fluid_id, 2) + 1, 3), dtype=np.uint8)
    for fid, color in FLUID_COLORS.items():
        lut[fid] = color
    return lut


class WorldViewer(tk.Tk):
    def __init__(
        self,
        world_blocks,
        fluid,
        blockinfo,
        id_image_mapping,
        id_color_mapping,
        tile_size=8,
        window_size=(1000, 800),
    ):
        super().__init__()
        self.title("spectra 2")
        self.geometry(f"{window_size[0]}x{window_size[1]}")
        self.configure(bg="#141423")
        self.world_blocks = world_blocks
        self.fluid = fluid
        self.blockinfo = blockinfo
        self.width, self.height = world_blocks.shape
        self.tile_size = tile_size
        self.DETAIL_THRESHOLD = max(tile_size / 2, 2.0)
        max_id = max(max(blockinfo), int(world_blocks.max()))
        self.color_lut = _build_color_lut(id_color_mapping, max_id)
        self.tile_atlas = _build_tile_atlas(id_image_mapping, max_id, tile_size)
        self.fluid_lut = _fluid_lut(int(fluid.max()) if fluid.size else 2)
        self._overview_rgb = self._make_overview()
        self.zoom = 5.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self._drag_start = None
        self._cursor_block = None
        self._tkimg = None
        self._build_ui()
        self._fit_to_window()
        self.after(50, self.render)

    def _make_overview(self):
        ids = np.flipud(self.world_blocks.T)
        rgb = self.color_lut[ids]
        fluid_ids = np.flipud(self.fluid.T)
        mask = fluid_ids != 0
        if mask.any():
            overlay = self.fluid_lut[fluid_ids]
            rgb = rgb.astype(np.float32)
            rgb[mask] = rgb[mask] * (1 - FLUID_ALPHA) + overlay[mask] * FLUID_ALPHA
            rgb = rgb.astype(np.uint8)
        return rgb

    def _build_ui(self):
        self.canvas = tk.Canvas(self, bg="#141423", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        status = ttk.Frame(self)
        status.pack(fill="x")
        self.status_var = tk.StringVar(value="")
        ttk.Label(status, textvariable=self.status_var).pack(side="left", padx=6)
        self.canvas.bind("<Configure>", self._on_configure)
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_move)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<MouseWheel>", self._on_zoom)
        self.canvas.bind("<Button-4>", lambda e: self._on_zoom(e, 1))
        self.canvas.bind("<Button-5>", lambda e: self._on_zoom(e, -1))
        self.bind("<Key-r>", lambda e: (self._fit_to_window(), self.render()))

    def _on_configure(self, event):
        self._fit_to_window()
        self.render()

    def _fit_to_window(self):
        self.update_idletasks()
        cw = self.canvas.winfo_width() or 1000
        ch = self.canvas.winfo_height() or 800
        self.zoom = max(
            min(cw / (self.width + 2), ch / (self.height + 2)),
            1 / 64,
        )

        self.offset_x = self.width / 2 - cw / self.zoom / 2
        self.offset_y = self.height / 2 - ch / self.zoom / 2

    def _on_drag_start(self, event):
        self._drag_start = event.x, event.y, self.offset_x, self.offset_y

    def _on_drag_move(self, event):
        if self._drag_start is None:
            return
        sx, sy, ox, oy = self._drag_start
        self.offset_x = ox - (event.x - sx) / self.zoom
        self.offset_y = oy + (event.y - sy) / self.zoom
        self.render()

    def _on_motion(self, event):
        ch = self.canvas.winfo_height() or 1
        array_x = int(np.floor(self.offset_x + event.x / self.zoom))
        array_y = int(np.floor(self.offset_y + (ch - 1 - event.y) / self.zoom))
        if 0 <= array_x < self.width and 0 <= array_y < self.height:
            self._cursor_block = array_x, self.height - 1 - array_y
        else:
            self._cursor_block = None
        self._update_status()

    def _on_zoom(self, event, direction=None):
        if direction is None:
            direction = 1 if event.delta > 0 else -1
        factor = 1.25**direction
        cw = self.canvas.winfo_width() or 1
        ch = self.canvas.winfo_height() or 1
        world_x = self.offset_x + event.x / self.zoom
        world_y = self.offset_y + (ch - event.y) / self.zoom
        self.zoom = min(max(self.zoom * factor, 1 / 8), float(self.tile_size) * 8)

        self.offset_x = world_x - event.x / self.zoom
        self.offset_y = world_y - (ch - event.y) / self.zoom
        self.render()

    def _clamp_offset(self):
        cw = self.canvas.winfo_width() or 1
        ch = self.canvas.winfo_height() or 1
        vis_w = cw / self.zoom
        vis_h = ch / self.zoom
        max_ox = self.width - vis_w
        max_oy = self.height - vis_h
        self.offset_x = min(max(self.offset_x, 0), max(max_ox, 0))
        self.offset_y = min(max(self.offset_y, 0), max(max_oy, 0))

    def _visible_block_range(self, cw, ch):
        wy_bottom = self.offset_y
        wy_top = self.offset_y + ch / self.zoom
        bx0 = max(int(np.floor(self.offset_x)), 0)
        by0 = max(int(np.floor(wy_bottom)), 0)
        bx1 = min(int(np.ceil(self.offset_x + cw / self.zoom)) + 1, self.width)
        by1 = min(int(np.ceil(wy_top)) + 1, self.height)
        bw = max(bx1 - bx0, 1)
        bh = max(by1 - by0, 1)
        return bx0, by0, bw, bh

    def render(self):
        cw = self.canvas.winfo_width() or 1000
        ch = self.canvas.winfo_height() or 800
        if self.zoom >= self.DETAIL_THRESHOLD:
            rgb = self._render_detail(cw, ch)
        else:
            rgb = self._render_overview(cw, ch)
        img = Image.fromarray(rgb, "RGB")
        self._tkimg = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._tkimg)
        self._update_status()

    def _update_status(self):
        mode = "detail" if self.zoom >= self.DETAIL_THRESHOLD else "overview"
        position = (
            "-"
            if self._cursor_block is None
            else f"{self._cursor_block[0]},{self._cursor_block[1]}"
        )
        tile_name = "-"
        if self._cursor_block is not None:
            cursor_x, cursor_y = self._cursor_block
            block_id = int(self.world_blocks[cursor_x, self.height - 1 - cursor_y])
            tile_name = self.blockinfo.get(block_id, f"unknown({block_id})")
        self.status_var.set(
            f"zoom={self.zoom:.2f}px/block  pos=({position})  tile={tile_name}  mode={mode}"
        )

    def _render_overview(self, cw, ch):
        ov_h, ov_w = self._overview_rgb.shape[:2]
        px = np.arange(cw, dtype=np.float32)
        py = np.arange(ch, dtype=np.float32)
        wx = (self.offset_x + px / self.zoom).astype(np.int32)
        wy_world = self.offset_y + (ch - 1 - py) / self.zoom
        wy_row = (ov_h - 1 - wy_world).astype(np.int32)
        valid_x = (wx >= 0) & (wx < ov_w)
        valid_y = (wy_row >= 0) & (wy_row < ov_h)
        wx = np.clip(wx, 0, ov_w - 1)
        wy_row = np.clip(wy_row, 0, ov_h - 1)
        out = self._overview_rgb[np.ix_(wy_row, wx)]
        out[~(valid_y[:, None] & valid_x[None, :])] = BACKGROUND_COLOR
        return out.astype(np.uint8)

    def _render_detail(self, cw, ch):
        bx0, by0, bw, bh = self._visible_block_range(cw, ch)
        t = self.tile_size
        block_crop = self.world_blocks[bx0 : bx0 + bw, by0 : by0 + bh]
        fluid_crop = self.fluid[bx0 : bx0 + bw, by0 : by0 + bh]
        ids = np.flipud(block_crop.T)
        fl = np.flipud(fluid_crop.T)
        tiles = self.tile_atlas[ids]
        tile_img = tiles.transpose(0, 2, 1, 3, 4).reshape(bh * t, bw * t, 3)
        mask = fl != 0
        if mask.any():
            tm = np.repeat(np.repeat(mask, t, axis=0), t, axis=1)
            ov = np.repeat(np.repeat(self.fluid_lut[fl], t, axis=0), t, axis=1)
            tile_img = tile_img.astype(np.float32)
            tile_img[tm] = tile_img[tm] * (1 - FLUID_ALPHA) + ov[tm] * FLUID_ALPHA
            tile_img = tile_img.astype(np.uint8)
        sub_x = (self.offset_x - bx0) * t
        top_world_y = self.offset_y + ch / self.zoom
        sub_y = (by0 + bh - top_world_y) * t
        px = np.arange(cw, dtype=np.float32)
        py = np.arange(ch, dtype=np.float32)
        tx = (sub_x + px / self.zoom * t).astype(np.int32)
        ty = (sub_y + py / self.zoom * t).astype(np.int32)
        valid_x = (tx >= 0) & (tx < bw * t)
        valid_y = (ty >= 0) & (ty < bh * t)
        tx = np.clip(tx, 0, bw * t - 1)
        ty = np.clip(ty, 0, bh * t - 1)
        out = np.empty((ch, cw, 3), dtype=np.uint8)
        out[:] = BACKGROUND_COLOR
        valid = valid_y[:, None] & valid_x[None, :]
        out[valid] = tile_img[np.ix_(ty, tx)][valid]
        return out.astype(np.uint8)


def show_world(
    gensettings, blockinfo, id_image_mapping=None, id_color_mapping=None, tile_size=8
):
    from worldgen_tools import (
        get_id_image_mapping,
        get_id_color_mapping as _get_id_color_mapping,
    )

    if id_image_mapping is None:
        id_image_mapping = get_id_image_mapping(blockinfo)
    if id_color_mapping is None:
        id_color_mapping = _get_id_color_mapping(blockinfo)
    app = WorldViewer(
        gensettings.worldBlocks,
        gensettings.fluid,
        blockinfo,
        id_image_mapping,
        id_color_mapping,
        tile_size=tile_size,
    )
    app.mainloop()
