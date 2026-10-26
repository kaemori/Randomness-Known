import pyfastnoiselite.pyfastnoiselite as _FNL


class FastNoiseLite(_FNL.FastNoiseLite):
    class NoiseType:
        Cellular = _FNL.NoiseType.NoiseType_Cellular
        Perlin = _FNL.NoiseType.NoiseType_Perlin
        OpenSimplex2 = _FNL.NoiseType.NoiseType_OpenSimplex2
        Value = _FNL.NoiseType.NoiseType_Value

    class FractalType:
        Ridged = _FNL.FractalType.FractalType_Ridged
        FBm = _FNL.FractalType.FractalType_FBm
        PingPong = _FNL.FractalType.FractalType_PingPong

    class CellularDistanceFunction:
        EuclideanSq = _FNL.CellularDistanceFunction.CellularDistanceFunction_EuclideanSq

    class CellularReturnType:
        Distance = _FNL.CellularReturnType.CellularReturnType_Distance

    class DomainWarpType:
        OpenSimplex2 = _FNL.DomainWarpType.DomainWarpType_OpenSimplex2
        BasicGrid = _FNL.DomainWarpType.DomainWarpType_BasicGrid

    def __init__(self, seed=0):
        super().__init__()
        self.seed = seed

    def SetNoiseType(self, v):
        self.noise_type = v

    def SetFrequency(self, v):
        self.frequency = v

    def SetFractalType(self, v):
        self.fractal_type = v

    def SetFractalOctaves(self, v):
        self.fractal_octaves = v

    def SetFractalLacunarity(self, v):
        self.fractal_lacunarity = v

    def SetFractalGain(self, v):
        self.fractal_gain = v

    def SetFractalWeightedStrength(self, v):
        self.fractal_weighted_strength = v

    def SetCellularDistanceFunction(self, v):
        self.cellular_distance_function = v

    def SetCellularReturnType(self, v):
        self.cellular_return_type = v

    def SetCellularJitter(self, v):
        self.cellular_jitter_modifier = v

    def SetDomainWarpType(self, v):
        self.domain_warp_type = v

    def SetDomainWarpAmp(self, v):
        self.domain_warp_amp = v

    def GetNoise(self, x, y):
        return self.get_noise(x, y)
