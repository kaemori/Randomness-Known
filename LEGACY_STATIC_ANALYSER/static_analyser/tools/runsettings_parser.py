import base64, gzip, json


def run_setting(setting_preset):
    return {
        d["Item1"]: d["Item2"]
        for d in json.loads(gzip.decompress(base64.b64decode(setting_preset)))
    }


def create_setting_preset(settings: dict) -> str:
    pairs = [{"Item1": k, "Item2": v} for k, v in settings.items()]
    payload = json.dumps(pairs, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(gzip.compress(payload)).decode("ascii")


if __name__ == "__main__":
    raw = "H4sIAAAAAAAAA32UTXLbMAyF76J16pHdpNPJDXqGThYQCUkY8y8gWMfp9O6FnIX1Y2rhjf35AQ8PxO+/zS9Bf2xemxLMSCmhbZ5u352a1x5cxn9Pd6aDjC5GsRgyyfVOtofnOTcxvjih5Aj5jh0P7VpOGNJG7tguwQmiYBj1D/OiCwh8RxjE0TDKDFrokEdHnma//1ipZAEWCkMuaWo+V5Q+0gAUqs48CnTRUfYMglVsRHBaa5fpGYwUxrSqd3pZjNIh2l0dCj0aoRhywnnINcyMEMxOW9QxOQcTulvXx2hDZK9OPx/Q7WHpI4aSNaIO2EeuZq0peQrAOGA9BBABc7bgYdhpjwIN4FHd2jzCeUaeVjV1xMlcjcP9CWIwxXc8Tc9AqmJZOJ7n+yVclo+NNfGv7vuPOtZHNnjrrc64eJliwD/6PnYqOnovZFPJoy5lHbOUexp0Jb3K1bEQb10xqlP62ryd06J7p0kIOsii6Ya9M6TnwCJvFnR7NJRSSQ8+lnmn3x+B+sJi3+tBunPf1pKTmNVUr7sb76I5J9IPo6GsvuskXFH33FJPj/ysDen16lAuiAH1SI3vBRYL1B5+LnD0CbVRDWpr7GUpHfW0roa0epgWuzJcIrtNMG//AcSjL3hFBgAA"
    a = run_setting(raw)
    a["healingrate"] = -0.25
    b = create_setting_preset(a)
    print(b)
    print(run_setting(b))
