import base64, zlib, json, re


def decode(s: str):
    return zlib.decompressobj(47).decompress(base64.b64decode(s)).decode("utf-8")


import gzip


def encode(s: str):
    return base64.b64encode(gzip.compress(s.encode("utf-8"))).decode("utf-8")


preset = "H4sIAAAAAAAAA32UTXLbMAyF76J16pHdpNPJDXqGThYQCUkY8y8gWMfp9O6FnIX1Y2rhjf35AQ8PxO+/zS9Bf2xemxLMSCmhbZ5u352a1x5cxn9Pd6aDjC5GsRgyyfVOtofnOTcxvjih5Aj5jh0P7VpOGNJG7tguwQmiYBj1D/OiCwh8RxjE0TDKDFrokEdHnma//1ipZAEWCkMuaWo+V5Q+0gAUqs48CnTRUfYMglVsRHBaa5fpGYwUxrSqd3pZjNIh2l0dCj0aoRhywnnINcyMEMxOW9QxOQcTulvXx2hDZK9OPx/Q7WHpI4aSNaIO2EeuZq0peQrAOGA9BBABc7bgYdhpjwIN4FHd2jzCeUaeVjV1xMlcjcP9CWIwxXc8Tc9AqmJZOJ7n+yVclo+NNfGv7vuPOtZHNnjrrc64eJliwD/6PnYqOnovZFPJoy5lHbOUexp0Jb3K1bEQb10xqlP62ryd06J7p0kIOsii6Ya9M6TnwCJvFnR7NJRSSQ8+lnmn3x+B+sJi3+tBunPf1pKTmNVUr7sb76I5J9IPo6GsvuskXFH33FJPj/ysDen16lAuiAH1SI3vBRYL1B5+LnD0CbVRDWpr7GUpHfW0roa0epgWuzJcIrtNMG//AcSjL3hFBgAA"
text = decode(preset)
print(json.dumps(json.loads(text), indent=2))

jsonpreset = json.loads(text)
# then edit like this
for pair in jsonpreset:
    if pair["Item1"] == "basetrapdensity":
        pair["Item2"] = 100.0
        break

print(encode(json.dumps(jsonpreset)))
