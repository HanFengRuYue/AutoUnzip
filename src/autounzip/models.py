from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class DisguisedExtensionRule:
    suffix: str
    enabled: bool = True


@dataclass(slots=True)
class AppSettings:
    password_library: list[str] = field(default_factory=list)
    disguised_extensions: list[DisguisedExtensionRule] = field(default_factory=list)
    default_output_dir: str | None = None
    cleanup_policy: str = "temporary_only"
    recent_inputs: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ArchiveGroup:
    entry_path: Path
    member_paths: list[Path]
    detection_source: str
    archive_type: str | None = None
    disguised_suffix: str | None = None
    volume_kind: str | None = None
    signature_hint: str | None = None


@dataclass(slots=True)
class ArchiveProbe:
    is_archive: bool
    archive_type: str | None = None
    needs_password: bool = False
    wrong_password: bool = False
    missing_volume: bool = False
    reason: str | None = None
    raw_output: str = ""


@dataclass(slots=True)
class DiscoverySkip:
    path: Path
    source: str
    reason: str


@dataclass(slots=True)
class ArchiveDiscovery:
    groups: list[ArchiveGroup] = field(default_factory=list)
    skipped: list[DiscoverySkip] = field(default_factory=list)


@dataclass(slots=True)
class ExtractionJob:
    input_path: Path
    output_dir: Path | None = None
    max_depth: int = 25


@dataclass(slots=True)
class ExtractionResult:
    final_output_dir: Path
    layers_processed: int = 0
    archives_extracted: int = 0
    warnings: list[str] = field(default_factory=list)
    password_sources: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PasswordRequest:
    archive_path: Path
    layer: int
    attempt_count: int
    message: str


@dataclass(slots=True)
class PasswordResponse:
    password: str | None
    save_to_library: bool = False
    cancel: bool = False


@dataclass(slots=True)
class CommandResult:
    success: bool
    output: str
    return_code: int
    needs_password: bool = False
    wrong_password: bool = False
    missing_volume: bool = False
    archive_type: str | None = None
    reason: str | None = None
