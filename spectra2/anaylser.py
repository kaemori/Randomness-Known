import numpy as np

filename = r"..\get_the_world_lol\worldblocks_depth0_1795417830.npy"
world = np.load(filename)

from cparser.csfunc import module_init
from spectra2 import show_world
from tools import textureloader
from tools.world_state import WorldState

world_state = WorldState.create(
    biome_depth=8 - 1,
    width=1024,
    height=1024,
    chunk_width=16,
    chunk_height=16,
    world_blocks=world,
)

module_init()


show_world(world_state, textureloader.get_blockinfo())
