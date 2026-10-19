from pyfastnoiselite.pyfastnoiselite import FastNoiseLite, NoiseType

caveNoise = FastNoiseLite(seed=0)
caveNoise.noise_type = NoiseType.NoiseType_Cellular
