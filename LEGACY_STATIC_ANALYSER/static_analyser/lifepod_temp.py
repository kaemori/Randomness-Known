num = this.chunkWidth * this.chunkHeight * amt * this.totalLootRarity
num2 = 0
while num2 < num:
    point = Vector2(Random.Range((-this.halfWidth + 32), this.halfWidth - 32), Random.Range((-this.halfWidth + 32), this.halfWidth - 32))
    raycastHit2D = Physics2D.Raycast(point, Vector2.down, 400.0, LayerMask.GetMask(string[] { "Ground" }))
    if raycastHit2D:
        point = raycastHit2D.point
    vector2Int = this.WorldToBlockPos(point)
    i = 0
    while i < 90:
        j = 0
        while j < 90:
            num3 = Vector2.Distance(point + Vector2.up * j + Vector2.right * i - Vector2.one * 45.0, point)
            if num3 < 45.0 * Random.Range(0.0, 12.0 / (num3 * 0.8)) and Random.Range(0.0, 1.0) < 0.7:
                vector2Int2 = this.WorldToBlockPos(point)
                vector2Int2.x += -45 + i
                vector2Int2.y += -45 + j + 2
                if vector2Int2.x < 0:
                    vector2Int2.x = 0
                if vector2Int2.x > ((this.width - 1)):
                    vector2Int2.x = (this.width - 1)
                if vector2Int2.y < 0:
                    vector2Int2.y = 0
                if vector2Int2.y > ((this.height - 1)):
                    vector2Int2.y = (this.height - 1)
                if this.worldBlocks[vector2Int2.x, vector2Int2.y] > 0:
                    worldBlocks[vector2Int2.x, vector2Int2.y] = Random.Range(0, 5)
            j += 1
        i += 1
    this.GenerateObjectAtPos(vector2Int, Resources.Load("Lifepod").transform.GetChild(0).GetComponent<Tilemap>(), 0.95, True)
    this.GenerateEntityAtPos(this.BlockToWorldPos(vector2Int), Resources.Load("Lifepod"))
    if Random.value < WorldGeneration.GetRunSettingFloat("traderchance") * 0.01:
        num4 = Random.Range(-4, 4)
        component = (Object.Instantiate(Resources.Load("trader" + Random.Range(1, 4).ToString()), this.BlockToWorldPos(vector2Int + Vector2.down * 7 + Vector2.right * num4) - Vector2.one * 0.5, Quaternion.identity) as GameObject).GetComponent<TraderScript>()
        if Mathf.Abs(num4) > 1.5:
            component.farEnoughToMove = True
        component.MoveRange = RangeF(this.BlockToWorldPos(vector2Int - Vector2.right * 5).x, this.BlockToWorldPos(vector2Int + Vector2.right * 5).x)
    else:
        Object.Instantiate(Resources.Load("lifepodchest"), this.BlockToWorldPos(vector2Int + Vector2.down * 6) - Vector2.one * 0.5, Quaternion.identity)
    k = 0
    while k < 3:
        if Random.Range(0.0, 1.0) < 0.05:
            Object.Instantiate(Resources.Load("experimentflesh"), point + Vector2.right * Random.Range(-3.0, 3.0), Quaternion.identity)
        k += 1
    if Random.Range(0.0, 1.0) < 0.05:
        Object.Instantiate(Resources.Load("internalorgans"), point + Vector2.right * Random.Range(-3.0, 3.0), Quaternion.identity)
    if Random.Range(0.0, 1.0) < 0.5:
        Object.Instantiate(Resources.Load("LoreNote"), point + Vector2.right * Random.Range(-3.0, 3.0) + Vector2.up * Random.Range(-1.0, -6.0), Quaternion.identity)
    if Random.Range(0.0, 1.0) < 0.285:
        Utils.Create("epda", point + Vector2.right * Random.Range(-3.0, 3.0), Random.value * 360.0)
    if Random.value < 0.2:
        vector = point + Vector2.right * Random.Range(-1.5, 1.5)
        Utils.Create("Special/defibrack", vector, 0.0)
        flag = Random.value < 0.5
        value = Random.value
        if Random.value < 0.75:
            gameObject = Utils.Create("manualdefibrillator", vector, 0.0)
            gameObject.AddComponent()
        else:
            gameObject = Utils.Create("aed", vector, 0.0)
            gameObject.AddComponent()
        if not flag:
            gameObject.GetComponent().battery.UnloadBattery(True)
        else:
            gameObject.GetComponent<Item>().condition = value
    num2 += 1
