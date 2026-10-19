from pyfastnoiselite.pyfastnoiselite import (
    FastNoiseLite,
    NoiseType,
    FractalType,
    CellularDistanceFunction,
    CellularReturnType,
)

# from pyfastnoiselite import pyfastnoiselite

dirtPerlinNoise = FastNoiseLite(seed=69)
dirtPerlinNoise.fractal_type = FractalType.FractalType_FBm
dirtPerlinNoise.noise_type = NoiseType.NoiseType_Perlin
dirtPerlinNoise.fractal_octaves = 3

print(dir(CellularReturnType))
# print(dir(pyfastnoiselite))
dirtPerlinNoise.cellular_jitter = 1.0

print(dirtPerlinNoise.get_noise(1, 2))
