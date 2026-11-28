import base64
import gzip
import json


DEFAULT_PRESET = (
    "H4sIAAAAAAAACn2UTW7bQAyF76J1aihuUhS5Qc9QZEHNUBLh+QuHU8cpevdSzkJ/GS28kT88PvJx+Ptv80vQPzYvTQlmpJTQNg/3b+fmRbjgv4cZ6SCji1Eshkxym8H29LTkJsYXJ5QcIc/Y46ndyglD2sl9X3MTQ8EwKl8VA98RBnE0jLIwttIhj448Lf7/0a5VsgALhSGXNHnPFaX3NACFqhePAl10lD2D1C2PCE5rHTI9g5HCmDb1zs+rSTpEe6hDoUcjFENOuIy4hpkRgjmwRR2TczChh3V9jDZE9trpxxd0e1r3EUPJGlEH7CMvsW1KngIwDlgPAUTAXCx4GA7sUaABPGq3No9wWZDnTU0dcTI34/B4ghhM8R1P0zOQqlgWjpflfu3eGmvin+779zrWRzZ491ZnXLxOMeAffR8HFR29FbKp5FGXso5Zyj0NupJe5epYiHdXjNopfW7eDPfgMm72TpMQdJBF0w32gNVzYJF3C9rujoZSKunBx7J0ur8uCuoLi32v92jmvm0lJzGrqd4ON95Fc0mkP0ZDWfuuk3BD3XNLPX3Vz7YhvV4dyhUxoB6p8a3AaoHa088Vjj6hGtWg9o09r6WjntbjIVnsynCN7HbBvP4HLP+un0MGAAA="
)


class RunSettings:
    def __init__(self, settings):
        self.settings = settings

    def GetRunSettingFloat(self, key):
        try:
            return self.settings[key]
        except KeyError as exc:
            raise KeyError(f"Run setting {key!r} is not configured") from exc

    @classmethod
    def from_preset_str(cls, preset):
        raw = json.loads(gzip.decompress(base64.b64decode(preset)))
        return cls({entry["Item1"]: entry["Item2"] for entry in raw})
