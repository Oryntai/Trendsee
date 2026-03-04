from enum import Enum


class TrendType(str, Enum):
    photo = "photo"
    video = "video"


class AssetKind(str, Enum):
    image = "image"
    video = "video"
    other = "other"


class GenerationStatus(str, Enum):
    queued = "queued"
    running = "running"
    done = "done"
    failed = "failed"
