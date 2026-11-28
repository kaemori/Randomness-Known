from __future__ import annotations
import pickle
import tkinter as tk
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import ttk
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageTk

to_rgb = lambda x: tuple(int(x[i : i + 2], 16) for i in (0, 2, 4))
FLUID_COLORS = {1: to_rgb("223355"), 2: to_rgb("224400"), 3: to_rgb("111111")}
FLUID_COLORS = {k: [col * 1 for col in v] for k, v in FLUID_COLORS.items()}
FLUID_ALPHA = 1
_FA = round(FLUID_ALPHA * 256)
_BACKGROUND_COLOR_RAW = [col // 3 for col in to_rgb("767676")]
BACKGROUND_COLOR = np.array(_BACKGROUND_COLOR_RAW, dtype=np.uint8)
BG_TUPLE = tuple(int(c) for c in BACKGROUND_COLOR)
ENTITY_IMAGE_PATH = Path(__file__).parent / "tools" / "hardcodedimages" / "entities"
ICON_CACHE_LIMIT = 512


def _blend(base, overlay):
    return (
        base.astype(np.uint16) * (256 - _FA) + overlay.astype(np.uint16) * _FA >> 8
    ).astype(np.uint8)


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
    size = max(max_fluid_id, *FLUID_COLORS) + 1
    lut = np.zeros((size, 3), dtype=np.uint8)
    for fid, color in FLUID_COLORS.items():
        lut[fid] = color
    return lut


def _load_entity_images(entities):
    images = {}
    names = {
        name
        for entity in entities or []
        for name in (entity.get("id"), entity.get("name"))
        if name
    }
    for name in names:
        image_path = ENTITY_IMAGE_PATH / f"{name}.png"
        if image_path.exists():
            images[name] = Image.open(image_path).convert("RGBA")
    return images


class WorldViewer(tk.Tk):
    def __init__(
        self,
        world_blocks,
        fluid,
        blockinfo,
        id_image_mapping,
        id_color_mapping,
        entities=None,
        debug_crosses=None,
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
        self.entities = entities or []
        self.debug_crosses = debug_crosses or []
        self.entity_images = _load_entity_images(self.entities)
        self.width, self.height = world_blocks.shape
        self.tile_size = tile_size
        self.DETAIL_THRESHOLD = max(tile_size / 2, 2.0)
        max_id = max(max(blockinfo), int(world_blocks.max()))
        self.color_lut = _build_color_lut(id_color_mapping, max_id)
        self.tile_atlas = _build_tile_atlas(id_image_mapping, max_id, tile_size)
        self.fluid_lut = _fluid_lut(int(fluid.max()) if fluid.size else 2)
        self._occupied = (world_blocks != 0) | (fluid != 0)
        self._overview_rgb = self._make_overview()
        self._entity_draw = self._prepare_entities()
        self._icon_cache = {}
        self.zoom = 5.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self._drag_start = None
        self._cursor_block = None
        self._tkimg = None
        self._img_item = None
        self._render_pending = False
        self._fitted = False
        self._last_status = None
        self._search_mode = False
        self._search_text = ""
        self._search_positions = np.empty((0, 2), dtype=np.intp)
        self._search_cache_id = None
        self._highlight_all = False
        self._cursor_px = None
        try:
            self._font = ImageFont.load_default(size=14)
        except TypeError:  # older Pillow
            self._font = ImageFont.load_default()
        self._build_ui()

    def _make_overview(self):
        rgb = self.color_lut[self.world_blocks]
        mask = self.fluid != 0
        if mask.any():
            rgb[mask] = _blend(rgb[mask], self.fluid_lut[self.fluid[mask]])
        return rgb

    def _prepare_entities(self):
        prepared = []
        for entity in self.entities:
            name = next(
                (
                    n
                    for n in (entity.get("id"), entity.get("name"))
                    if n in self.entity_images
                ),
                None,
            )
            position = entity.get("position", {})
            if name is None or "x" not in position or "y" not in position:
                continue
            scale = entity.get("scale", {})
            rot = entity.get("rotation_deg", 0.0)
            rot = float(rot[2]) if isinstance(rot, list) else float(rot)
            length = (
                float(entity["length"])
                if entity.get("length") and entity.get("id") == "ladder"
                else 0.0
            )
            prepared.append(
                (
                    name,
                    float(position["x"]),
                    float(position["y"]),
                    float(scale.get("x", 1.0)),
                    float(scale.get("y", 1.0)),
                    rot,
                    length,
                )
            )
        return prepared

    def _build_ui(self):
        self.canvas = tk.Canvas(self, bg="#141423", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        status = ttk.Frame(self)
        status.pack(fill="x")
        self.status_var = tk.StringVar(value="")
        ttk.Label(status, textvariable=self.status_var).pack(side="left", padx=6)
        self.search_status_var = tk.StringVar(value="")
        ttk.Label(status, textvariable=self.search_status_var, anchor="e").pack(
            side="right", padx=6
        )
        self.canvas.bind("<Configure>", self._on_configure)
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_move)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<MouseWheel>", self._on_zoom)
        self.canvas.bind("<Button-4>", lambda e: self._on_zoom(e, 1))
        self.canvas.bind("<Button-5>", lambda e: self._on_zoom(e, -1))
        self.bind("<Key-r>", lambda e: (self._fit_to_window(), self.request_render()))
        self.bind("<Key>", self._on_key)

    def _on_configure(self, event):
        if not self._fitted:
            self._fit_to_window()
            self._fitted = True
        self.request_render()

    def _fit_to_window(self):
        cw = self.canvas.winfo_width() or 1000
        ch = self.canvas.winfo_height() or 800
        self.zoom = max(min(cw / (self.width + 2), ch / (self.height + 2)), 1 / 64)
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
        self.request_render()

    def _on_motion(self, event):
        self._cursor_px = (event.x, event.y)
        ch = self.canvas.winfo_height() or 1
        x = int(np.floor(self.offset_x + event.x / self.zoom))
        y = int(np.floor(self.offset_y + (ch - 1 - event.y) / self.zoom))
        self._cursor_block = (
            (x, y) if 0 <= x < self.width and 0 <= y < self.height else None
        )
        self._update_status()
        if self._search_mode:
            self.request_render()

    def _on_key(self, event):
        if event.keysym.lower() == "f":
            self._search_mode = not self._search_mode
            self._search_text = ""
            self._search_cache_id = None
        elif event.keysym.lower() == "g":
            self._highlight_all = not self._highlight_all
        elif self._search_mode:
            if event.char.isdigit():
                if len(self._search_text) >= 2:  # start a fresh id
                    self._search_text = ""
                self._search_text += event.char
            elif event.keysym == "BackSpace":
                self._search_text = self._search_text[:-1]
        else:
            return
        self.request_render()

    def _search_target(self):
        """Nearest block of the searched id to the cursor block, or None."""
        if not self._search_text:
            return None
        bid = int(self._search_text)
        if self._search_cache_id != bid:
            self._search_cache_id = bid
            self._search_positions = np.argwhere(self.world_blocks == bid)
        pos = self._search_positions
        if len(pos) == 0 or self._cursor_block is None:
            return None
        d = ((pos - np.array(self._cursor_block)) ** 2).sum(axis=1)
        return tuple(int(v) for v in pos[d.argmin()])

    def _draw_search(self, image, cw, ch):
        if not self._search_mode:
            return
        draw = ImageDraw.Draw(image)
        target = self._search_target()
        if self._highlight_all and self._search_text:
            r = max(2, round(self.zoom / 2))
            for bx, by in self._search_positions:
                tx = round((int(bx) + 0.5 - self.offset_x) * self.zoom)
                ty = round(ch - (int(by) + 0.5 - self.offset_y) * self.zoom)
                if tx + r < 0 or tx - r > cw or ty + r < 0 or ty - r > ch:
                    continue
                draw.ellipse(
                    (tx - r, ty - r, tx + r, ty + r), outline="#999933", width=1
                )
        if target is not None and self._cursor_px is not None:
            tx = round((target[0] + 0.5 - self.offset_x) * self.zoom)
            ty = round(ch - (target[1] + 0.5 - self.offset_y) * self.zoom)
            draw.line((*self._cursor_px, tx, ty), fill="#ffff33", width=2)
            r = max(4, round(self.zoom / 2))
            draw.ellipse((tx - r, ty - r, tx + r, ty + r), outline="#ffff33", width=2)

    def _on_zoom(self, event, direction=None):
        if direction is None:
            direction = 1 if event.delta > 0 else -1
        ch = self.canvas.winfo_height() or 1
        world_x = self.offset_x + event.x / self.zoom
        world_y = self.offset_y + (ch - event.y) / self.zoom
        self.zoom = min(
            max(self.zoom * 1.25**direction, 1 / 8), float(self.tile_size) * 8
        )
        self.offset_x = world_x - event.x / self.zoom
        self.offset_y = world_y - (ch - event.y) / self.zoom
        self.request_render()

    def request_render(self):
        if not self._render_pending:
            self._render_pending = True
            self.after_idle(self._render_now)

    render = request_render

    def _grid(self, cw, ch):
        fx = self.offset_x + np.arange(cw) / self.zoom
        fy = self.offset_y + (ch - 1 - np.arange(ch)) / self.zoom
        fxl, fyl = np.floor(fx), np.floor(fy)
        wx = fxl.astype(np.intp)
        wy = fyl.astype(np.intp)
        vx = (wx >= 0) & (wx < self.width)
        vy = (wy >= 0) & (wy < self.height)
        np.clip(wx, 0, self.width - 1, out=wx)
        np.clip(wy, 0, self.height - 1, out=wy)
        return fx - fxl, fy - fyl, wx, wy, vx, vy

    def _render_overview(self, cw, ch):
        _, _, wx, wy, vx, vy = self._grid(cw, ch)
        ix, iy = wx[None, :], wy[:, None]
        rgb = self._overview_rgb[ix, iy]
        occ = self._occupied[ix, iy]
        occ &= vy[:, None] & vx[None, :]
        return rgb, occ

    def _render_detail(self, cw, ch):
        t = self.tile_size
        fracx, fracy, wx, wy, vx, vy = self._grid(cw, ch)
        u = np.minimum((fracx * t).astype(np.intp), t - 1)
        v = t - 1 - np.minimum((fracy * t).astype(np.intp), t - 1)
        ix, iy = wx[None, :], wy[:, None]
        ids = self.world_blocks[ix, iy]
        rgb = self.tile_atlas[ids, v[:, None], u[None, :]]
        fl = self.fluid[ix, iy]
        m = fl != 0
        if m.any():
            rgb[m] = _blend(rgb[m], self.fluid_lut[fl[m]])
        occ = (ids != 0) | m
        occ &= vy[:, None] & vx[None, :]
        return rgb, occ

    def _render_now(self):
        self._render_pending = False
        cw = self.canvas.winfo_width() or 1000
        ch = self.canvas.winfo_height() or 800
        if self.zoom >= self.DETAIL_THRESHOLD:
            rgb, occ = self._render_detail(cw, ch)
        else:
            rgb, occ = self._render_overview(cw, ch)
        sprites = self._entity_sprites(cw, ch)
        if sprites:
            img = Image.new("RGB", (cw, ch), BG_TUPLE)
            for sprite, x, y in sprites:
                img.paste(sprite, (x, y), sprite)
            img.paste(
                Image.fromarray(rgb), (0, 0), Image.fromarray(occ.view(np.uint8) * 255)
            )
        else:
            rgb[~occ] = BACKGROUND_COLOR
            img = Image.fromarray(rgb)
        self._draw_debug_crosses(img, cw, ch)
        self._draw_search(img, cw, ch)
        if (
            self._tkimg is None
            or self._tkimg.width() != cw
            or self._tkimg.height() != ch
        ):
            self._tkimg = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self._img_item = self.canvas.create_image(
                0, 0, anchor="nw", image=self._tkimg
            )
        else:
            self._tkimg.paste(img)
        self._update_status()

    def _update_status(self):
        mode = "detail" if self.zoom >= self.DETAIL_THRESHOLD else "overview"
        if self._cursor_block is None:
            position, tile_name, liquid_id = "-", "-", "-"
        else:
            cx, cy = self._cursor_block
            position = f"{cx},{cy}"
            block_id = int(self.world_blocks[cx, cy])
            tile_name = self.blockinfo.get(block_id, f"unknown({block_id})")
            liquid_id = int(self.fluid[cx, cy])
        text = f"zoom={self.zoom:.2f}px/block  pos=({position})  tile={tile_name} (liquid={liquid_id})  mode={mode}"
        if text != self._last_status:
            self._last_status = text
            self.status_var.set(text)
        self._update_search_status()

    def _update_search_status(self):
        if not self._search_mode:
            self.search_status_var.set("")
            return
        search_id = self._search_text or "__"
        text = f"Search id: {search_id}"
        if self._search_text:
            bid = int(self._search_text)
            name = self.blockinfo.get(bid, f"unknown({bid})")
            text += f"  |  Block: {name}"
            if len(self._search_positions) == 0:
                text += "  |  Not found in world"
            else:
                target = self._search_target()
                if target is None:
                    text += "  |  Move cursor over the world"
                else:
                    text += f"  |  Nearest at: ({target[0]}, {target[1]})"
        self.search_status_var.set(text)

    def _entity_sprites(self, cw, ch):
        if not self._entity_draw:
            return []
        out = []
        zoom = self.zoom
        scale = zoom / self.tile_size
        cache = self._icon_cache
        for name, px, py, sx, sy, rot, length in self._entity_draw:
            icon = self.entity_images[name]
            w = max(round(icon.width * scale * abs(sx)), 2)
            h = (
                max(round(length * zoom * abs(sy)), 2)
                if length
                else max(round(icon.height * scale * abs(sy)), 2)
            )
            x = round((px - self.offset_x) * zoom)
            y = round(ch - (py - self.offset_y) * zoom)
            half = (w + h) // 2 + 1
            if x + half < 0 or x - half > cw or y + half < 0 or y - half > ch:
                continue
            key = name, w, h, sx < 0, sy < 0, rot
            sprite = cache.get(key)
            if sprite is None:
                sprite = icon.resize((w, h), Image.Resampling.NEAREST)
                if sx < 0:
                    sprite = sprite.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                if sy < 0:
                    sprite = sprite.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                if rot:
                    sprite = sprite.rotate(
                        rot, expand=True, resample=Image.Resampling.NEAREST
                    )
                if len(cache) >= ICON_CACHE_LIMIT:
                    cache.clear()
                cache[key] = sprite
            out.append((sprite, x - sprite.width // 2, y - sprite.height // 2))
        return out

    def _draw_debug_crosses(self, image, cw, ch):
        if not self.debug_crosses:
            return
        draw = ImageDraw.Draw(image)
        arm = max(4, round(self.zoom * 2))
        width = max(1, round(self.zoom / 3))
        zoom, ox, oy = self.zoom, self.offset_x, self.offset_y
        for bx, by in self.debug_crosses:
            x = round((float(bx) + 0.5 - ox) * zoom)
            y = round(ch - (float(by) + 0.5 - oy) * zoom)
            if x + arm < 0 or x - arm > cw or y + arm < 0 or y - arm > ch:
                continue
            draw.line((x - arm, y, x + arm, y), fill="#ff3333", width=width)
            draw.line((x, y - arm, x, y + arm), fill="#ff3333", width=width)


@dataclass
class WorldFile:
    world_blocks: np.ndarray
    fluid: np.ndarray
    blockinfo: dict
    id_image_mapping: dict | None = None
    id_color_mapping: dict | None = None
    entities: list = field(default_factory=list)
    debug_crosses: list = field(default_factory=list)
    tile_size: int = 8

    @classmethod
    def from_world_state(
        cls,
        world_state,
        blockinfo,
        id_image_mapping=None,
        id_color_mapping=None,
        entities=None,
        tile_size=8,
    ):
        return cls(
            world_blocks=world_state.world_blocks,
            fluid=world_state.fluid,
            blockinfo=blockinfo,
            id_image_mapping=id_image_mapping,
            id_color_mapping=id_color_mapping,
            entities=(
                entities
                if entities is not None
                else getattr(world_state, "world_block_entities", [])
            ),
            debug_crosses=getattr(world_state, "debug_crosses", []),
            tile_size=tile_size,
        )

    from_gensettings = from_world_state

    def save(self, path="worldsaved.bin"):
        with open(path, "wb") as f:
            pickle.dump(self, f, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load(cls, path="worldsaved.bin"):
        with open(path, "rb") as f:
            return pickle.load(f)

    def show(self):
        from tools.textureloader import (
            get_id_image_mapping,
            get_id_color_mapping as _get_id_color_mapping,
        )

        id_image_mapping = self.id_image_mapping
        if id_image_mapping is None:
            id_image_mapping = get_id_image_mapping(self.blockinfo)
        id_color_mapping = self.id_color_mapping
        if id_color_mapping is None:
            id_color_mapping = _get_id_color_mapping(self.blockinfo)
        print(self.blockinfo)
        app = WorldViewer(
            self.world_blocks,
            self.fluid,
            self.blockinfo,
            id_image_mapping,
            id_color_mapping,
            entities=self.entities,
            debug_crosses=getattr(self, "debug_crosses", []),
            tile_size=self.tile_size,
        )
        app.mainloop()


def show_world(
    world_state,
    blockinfo,
    id_image_mapping=None,
    id_color_mapping=None,
    entities=None,
    tile_size=8,
):
    from tools.textureloader import (
        get_id_image_mapping,
        get_id_color_mapping as _get_id_color_mapping,
    )

    if id_image_mapping is None:
        id_image_mapping = get_id_image_mapping(blockinfo)
    if id_color_mapping is None:
        id_color_mapping = _get_id_color_mapping(blockinfo)
    app = WorldViewer(
        world_state.world_blocks,
        world_state.fluid,
        blockinfo,
        id_image_mapping,
        id_color_mapping,
        entities=entities,
        debug_crosses=getattr(world_state, "debug_crosses", []),
        tile_size=tile_size,
    )
    app.mainloop()


if __name__ == "__main__":
    WorldFile.load().show()
