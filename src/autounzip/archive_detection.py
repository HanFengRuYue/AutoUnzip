from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Callable

from .models import AppSettings, ArchiveDiscovery, ArchiveGroup, ArchiveProbe, DiscoverySkip

STANDARD_SINGLE_EXTENSIONS = {
    ".7z",
    ".zip",
    ".rar",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".cab",
    ".iso",
}
STANDARD_MULTI_EXTENSIONS = {
    ".tar.gz",
    ".tar.bz2",
    ".tar.xz",
    ".tgz",
    ".tbz2",
    ".txz",
}

_PART_RAR_RE = re.compile(r"^(?P<base>.+)\.part(?P<num>\d+)\.rar$", re.IGNORECASE)
_EXT_NUMERIC_RE = re.compile(
    r"^(?P<base>.+\.(?:7z|zip))\.(?P<num>\d{3})$", re.IGNORECASE
)
_GENERIC_NUMERIC_RE = re.compile(r"^(?P<base>.+)\.(?P<num>\d{3})$", re.IGNORECASE)
_Z_SPLIT_RE = re.compile(r"^(?P<base>.+)\.z(?P<num>\d{2})$", re.IGNORECASE)


def guess_archive_type_from_signature(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    with path.open("rb") as handle:
        head = handle.read(512)
    if head.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return "zip"
    if head.startswith(b"7z\xbc\xaf'\x1c"):
        return "7z"
    if head.startswith((b"Rar!\x1a\x07\x00", b"Rar!\x1a\x07\x01\x00")):
        return "rar"
    if head.startswith(b"\x1f\x8b"):
        return "gzip"
    if head.startswith(b"BZh"):
        return "bzip2"
    if head.startswith(b"\xfd7zXZ\x00"):
        return "xz"
    if len(head) > 262 and head[257:262] == b"ustar":
        return "tar"
    return None


def discover_archives(
    root: Path,
    settings: AppSettings,
    probe: Callable[[Path], ArchiveProbe] | None = None,
) -> ArchiveDiscovery:
    file_paths, restrict_to = _collect_file_paths(root)
    grouped = _build_groups(file_paths)
    enabled_disguised = {
        rule.suffix.lower()
        for rule in settings.disguised_extensions
        if rule.enabled and rule.suffix
    }
    discovery = ArchiveDiscovery()
    for entry_path, member_paths, volume_kind in grouped:
        if restrict_to is not None and restrict_to not in member_paths and restrict_to != entry_path:
            continue
        detection_source, disguised_suffix = _classify_candidate(
            entry_path, enabled_disguised, volume_kind
        )
        if detection_source is None:
            continue
        signature_hint = guess_archive_type_from_signature(entry_path)
        accepted = False
        archive_type = signature_hint
        reason = ""

        if signature_hint is not None:
            accepted = True
        elif probe is not None:
            probe_result = probe(entry_path)
            archive_type = probe_result.archive_type or archive_type
            accepted = (
                probe_result.is_archive
                or probe_result.needs_password
                or probe_result.missing_volume
            )
            reason = probe_result.reason or "7-Zip 验证未通过"
        else:
            accepted = detection_source != "disguised_extension"
            reason = "缺少内容验证器"

        if accepted:
            discovery.groups.append(
                ArchiveGroup(
                    entry_path=entry_path,
                    member_paths=member_paths,
                    detection_source=detection_source,
                    archive_type=archive_type,
                    disguised_suffix=disguised_suffix,
                    volume_kind=volume_kind,
                    signature_hint=signature_hint,
                )
            )
        else:
            discovery.skipped.append(
                DiscoverySkip(
                    path=entry_path,
                    source=detection_source,
                    reason=reason or "内容验证失败，已跳过",
                )
            )
    discovery.groups.sort(key=lambda item: str(item.entry_path).lower())
    discovery.skipped.sort(key=lambda item: str(item.path).lower())
    return discovery


def archive_display_stem(group: ArchiveGroup) -> str:
    name = group.entry_path.name
    lower = name.lower()
    if group.volume_kind == "zip_z":
        return group.entry_path.stem
    if group.volume_kind == "part_rar":
        match = _PART_RAR_RE.match(name)
        if match:
            return Path(match.group("base")).stem
    if group.volume_kind in {"generic_numeric", "ext_numeric"}:
        return name.rsplit(".", 1)[0]
    if len(group.entry_path.suffixes) >= 2:
        combined = "".join(s.lower() for s in group.entry_path.suffixes[-2:])
        if combined in STANDARD_MULTI_EXTENSIONS:
            return name[: -len(combined)]
    if lower.endswith(tuple(STANDARD_SINGLE_EXTENSIONS)):
        return group.entry_path.stem
    return group.entry_path.stem


def _collect_file_paths(root: Path) -> tuple[list[Path], Path | None]:
    if root.is_file():
        candidates = [path for path in root.parent.iterdir() if path.is_file()]
        return candidates, root
    return [path for path in root.rglob("*") if path.is_file()], None


def _classify_candidate(
    entry_path: Path, enabled_disguised: set[str], volume_kind: str | None
) -> tuple[str | None, str | None]:
    lower_suffix = entry_path.suffix.lower()
    if volume_kind is not None:
        return "volume_sequence", None

    combined_suffix = "".join(s.lower() for s in entry_path.suffixes[-2:])
    if lower_suffix in STANDARD_SINGLE_EXTENSIONS or combined_suffix in STANDARD_MULTI_EXTENSIONS:
        return "standard_extension", None

    if lower_suffix in enabled_disguised:
        return "disguised_extension", lower_suffix

    return None, None


def _build_groups(file_paths: list[Path]) -> list[tuple[Path, list[Path], str | None]]:
    by_parent: dict[Path, list[Path]] = defaultdict(list)
    for path in file_paths:
        by_parent[path.parent].append(path)

    groups: list[tuple[Path, list[Path], str | None]] = []
    for directory, paths in by_parent.items():
        assigned: set[Path] = set()
        lower_map = {path.name.lower(): path for path in paths}
        sorted_paths = sorted(paths, key=lambda item: item.name.lower())

        for path in sorted_paths:
            if path in assigned:
                continue
            lower_name = path.name.lower()

            if lower_name.endswith(".zip"):
                z_prefix = f"{path.stem.lower()}.z"
                z_members = [
                    candidate
                    for candidate in sorted_paths
                    if candidate not in assigned
                    and _Z_SPLIT_RE.match(candidate.name.lower())
                    and candidate.name.lower().startswith(z_prefix)
                ]
                if z_members:
                    members = [path, *sorted(z_members, key=_numeric_volume_sort)]
                    assigned.update(members)
                    groups.append((path, members, "zip_z"))
                    continue

            part_match = _PART_RAR_RE.match(lower_name)
            if part_match and int(part_match.group("num")) == 1:
                prefix = f"{part_match.group('base')}.part"
                members = [
                    candidate
                    for candidate in sorted_paths
                    if candidate not in assigned
                    and candidate.name.lower().startswith(prefix)
                    and candidate.name.lower().endswith(".rar")
                ]
                members = sorted(members, key=_numeric_volume_sort)
                assigned.update(members)
                groups.append((path, members, "part_rar"))
                continue

            ext_numeric_match = _EXT_NUMERIC_RE.match(lower_name)
            if ext_numeric_match and ext_numeric_match.group("num") == "001":
                base = ext_numeric_match.group("base")
                members = [
                    candidate
                    for candidate in sorted_paths
                    if candidate not in assigned
                    and candidate.name.lower().startswith(f"{base}.")
                    and _EXT_NUMERIC_RE.match(candidate.name.lower())
                ]
                members = sorted(members, key=_numeric_volume_sort)
                assigned.update(members)
                groups.append((path, members, "ext_numeric"))
                continue

            generic_match = _GENERIC_NUMERIC_RE.match(lower_name)
            if (
                generic_match
                and generic_match.group("num") == "001"
                and _EXT_NUMERIC_RE.match(lower_name) is None
            ):
                base = generic_match.group("base")
                members = [
                    candidate
                    for candidate in sorted_paths
                    if candidate not in assigned
                    and candidate.name.lower().startswith(f"{base}.")
                    and _GENERIC_NUMERIC_RE.match(candidate.name.lower())
                ]
                members = sorted(members, key=_numeric_volume_sort)
                assigned.update(members)
                groups.append((path, members, "generic_numeric"))
                continue

            assigned.add(path)
            groups.append((path, [path], None))

    groups.sort(key=lambda item: str(item[0]).lower())
    return groups


def _numeric_volume_sort(path: Path) -> tuple[int, str]:
    name = path.name.lower()
    match = _PART_RAR_RE.match(name)
    if match:
        return int(match.group("num")), name
    match = _EXT_NUMERIC_RE.match(name)
    if match:
        return int(match.group("num")), name
    match = _GENERIC_NUMERIC_RE.match(name)
    if match:
        return int(match.group("num")), name
    match = _Z_SPLIT_RE.match(name)
    if match:
        return int(match.group("num")), name
    return 0, name
