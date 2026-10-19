for_fixer = lambda x: math.ceil(x) if isinstance(x, float) else x
private void GenerateOres() {
runSettingFloat = WorldGeneration.GetRunSettingFloat("oreamount")
i = Mathf.RoundToInt((this.chunkWidth * this.chunkHeight / 2U) * runSettingFloat)
while i > 0:
    vector2Int = (Random.Range(0.0, this.width), Random.Range(0.0, this.height))
    j = Random.Range(1, 26)
    while j > 0:
        if vector2Int.x > 0 and vector2Int.x < ((this.width - 1U)) and vector2Int.y > 0 and vector2Int.y < ((this.height - 1U)) and this.worldBlocks[vector2Int.x, vector2Int.y] > 0:
            worldBlocks[vector2Int.x, vector2Int.y] = 34
        vector2Int +== ((Random.value > 0.5) ? (1 if (Random.value > 0.5) else (-1)) : 0, (Random.value > 0.5) ? (1 if (Random.value > 0.5) else (-1)) : 0)
        j -= 1
    i -= 1
if this.biomeDepth < 4:
    return
num = 0
num2 = Mathf.RoundToInt(1024.0 / Mathf.Clamp(runSettingFloat, 0.01, 999.0))
num3 = 0
while num3 < this.width:
    num4 = 0
    while num4 < this.height:
        num += 1
        if num > num2 and Random.value < 0.001:
            if this.worldBlocks[num3, num4] > 0:
                worldBlocks[num3, num4] = 35
            num = 0
        num4 += 1
    num3 += 1
