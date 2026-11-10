"""Central configuration: environment variables plus an optional YAML file.

Defaults reproduce the v0 baseline (D0): no iteration cap, no temperature, real tool backend.
"""
import hashlib
import json
import os
from dataclasses import asdict, dataclass, field

DEFENSE_LEVELS = ("D0", "D1", "D2", "D3")
MODULES = ("M1", "M2", "M3")


@dataclass(frozen=True)
class Config:
    defense: str = "D0"
    modules: tuple = ()
    provider: str = "openai"
    model: str = "gpt-5.4-mini"
    temperature: float | None = None  # None = parameter not sent (baseline behaviour)
    max_iterations: int | None = None  # None = no cap (baseline behaviour)
    test_mode: bool = False  # True forces the mock backend; real Pushover is never used
    log_path: str | None = None
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.defense not in DEFENSE_LEVELS:
            raise ValueError(f"unknown defense level {self.defense!r}")
        bad = [m for m in self.modules if m not in MODULES]
        if bad:
            raise ValueError(f"unknown modules {bad!r}")

    def level(self) -> int:
        return DEFENSE_LEVELS.index(self.defense)

    def enabled(self, flag: str) -> bool:
        """flag is 'D1'..'D3' (true when the level is at least that) or 'M1'..'M3'."""
        if flag in MODULES:
            return flag in self.modules
        return self.level() >= DEFENSE_LEVELS.index(flag)

    def config_hash(self) -> str:
        blob = json.dumps(asdict(self), sort_keys=True, default=list)
        return hashlib.sha256(blob.encode()).hexdigest()[:12]


def _parse_float(v):
    return None if v in (None, "", "none") else float(v)


def load_config(yaml_path: str | None = None, env: dict | None = None) -> Config:
    """YAML file first, then TWIN_* environment variables override it."""
    env = os.environ if env is None else env
    data: dict = {}
    yaml_path = yaml_path or env.get("TWIN_CONFIG")
    if yaml_path:
        import yaml

        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    mapping = {
        "TWIN_DEFENSE": "defense", "TWIN_PROVIDER": "provider", "TWIN_MODEL": "model",
        "TWIN_TEMPERATURE": "temperature", "TWIN_MAX_ITERATIONS": "max_iterations",
        "TWIN_TEST_MODE": "test_mode", "TWIN_LOG_PATH": "log_path", "TWIN_MODULES": "modules",
    }
    for key, name in mapping.items():
        if key in env:
            data[name] = env[key]
    if "temperature" in data:
        data["temperature"] = _parse_float(data["temperature"])
    if data.get("max_iterations") is not None:
        data["max_iterations"] = int(data["max_iterations"])
    if isinstance(data.get("modules"), str):
        data["modules"] = tuple(m for m in data["modules"].split(",") if m)
    if "modules" in data:
        data["modules"] = tuple(data["modules"])
    if isinstance(data.get("test_mode"), str):
        data["test_mode"] = data["test_mode"].lower() in ("1", "true", "yes")
    return Config(**data)
