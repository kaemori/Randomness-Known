GenerateDropCapsules(xs_range_float(0.12, 0.13))
GenerateCollapsedPods(xs_range_float(0.066, 0.077))
num9 = chunkWidth * chunkHeight * xs_range_float(0.9, 1.1)
num10 = 0
while num10 < num9:
    raycastHit2D12 = Physics2D.Raycast(Vector2(xs_range_ambig(0 - int(halfWidth), halfWidth), xs_range_ambig(0 - int(halfHeight), halfHeight)), Vector2.down, CHUNKSIZE, LayerMask.GetMask('Ground'))
    if raycastHit2D12:
        GenerateTree(WorldToBlockPos(raycastHit2D12.point))
    num10 += 1
num = chunkWidth * chunkHeight * xs_range_float(0.06, 0.08) * totalLootRarity
try_generate_specific(num, 'Structures/CratePod', 0.82, True, ground=True, entity=True, circles=[(16, 3, 0.5, 0.0, True), (20, 4, 0.2, 0.0, True)])
try_generate_specific(num, 'Structures/MiniPod', 0.88, True, ground=True, entity=True, circles=[(16, 3, 0.5, 0.0, True), (20, 4, 0.2, 0.0, True)])
num = chunkWidth * chunkHeight * xs_range_float(0.03, 0.05) * totalLootRarity
try_generate_specific(num, 'Structures/WoodCross', 0.95, True, ground=True, entity=False)
num = chunkWidth * chunkHeight * xs_range_float(0.03, 0.05) * totalLootRarity
try_generate_specific(num, 'Structures/WoodHorizontal', 0.95, True, ground=True, entity=False)
num = chunkWidth * chunkHeight * xs_range_float(0.04, 0.05) * totalLootRarity
try_generate_specific(num, 'Structures/BrickLoot', 0.925, True, ground=True, entity=True)
num = chunkWidth * chunkHeight * xs_range_float(0.03, 0.04) * totalLootRarity
try_generate_specific(num, 'BioContainer', 0.975, True, ground=True, entity=True, child_index=0, circles=[(16, 3, 0.8, 0.0, True), (20, 4, 0.3, 0.0, True), (16, 0, 0.15, 0.0, True)])
num = chunkWidth * chunkHeight * xs_range_float(0.35, 0.5)
num17 = 0
while num17 < num:
    vector2Int = Vector2Int(xs_range_int(0, int(width)), xs_range_int(0, int(height)))
    num18 = xs_range_int(1, 5)
    num19 = 0
    while num19 < num18:
        num20 = 0
        while num20 < 1:
            if vector2Int.x + num19 < width and vector2Int.y + num20 < height:
                worldBlocks[num19 + vector2Int.x, num20 + vector2Int.y] = 5
            num20 += 1
        num19 += 1
    num17 += 1
num = chunkWidth * chunkHeight * xs_range_float(0.35, 0.5)
num21 = 0
while num21 < num:
    vector2Int2 = Vector2Int(xs_range_int(0, int(width)), xs_range_int(0, int(height)))
    num22 = xs_range_int(1, 5)
    num23 = 0
    while num23 < num22:
        num24 = 0
        while num24 < 2:
            if vector2Int2.x + num24 < width and vector2Int2.y + num23 < height:
                worldBlocks[num24 + vector2Int2.x, num23 + vector2Int2.y] = 5
            num24 += 1
        num23 += 1
    num21 += 1
GenerateLifePods(xs_range_float(0.088, 0.1))
