import base64
import gzip
import json
from dataclasses import dataclass


@dataclass(slots=True)
class RunSettings:
    settings: dict

    def GetRunSettingFloat(self, query):
        return self.settings[query]

    @staticmethod
    def from_preset_str(preset):
        raw = json.loads(gzip.decompress(base64.b64decode(preset)))
        return RunSettings({d["Item1"]: d["Item2"] for d in raw})
