from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Protocol

from .archive_detection import archive_display_stem, discover_archives
from .models import (
    AppSettings,
    ArchiveGroup,
    ArchiveProbe,
    CommandResult,
    ExtractionJob,
    ExtractionResult,
    PasswordRequest,
    PasswordResponse,
)
from .settings import AppSettingsStore
from .vendor import sevenzip_binary


class ArchiveTool(Protocol):
    def probe(self, archive_path: Path) -> ArchiveProbe: ...

    def extract(
        self,
        archive_path: Path,
        destination: Path,
        password: str | None,
        is_cancelled: Callable[[], bool],
        log: Callable[[str], None],
    ) -> CommandResult: ...


class SevenZipTool:
    def __init__(self, binary_path: Path | None = None) -> None:
        self.binary_path = binary_path or sevenzip_binary()
        self.creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    def probe(self, archive_path: Path) -> ArchiveProbe:
        command = [str(self.binary_path), "l", "-slt", "-sccUTF-8", str(archive_path)]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=self.creationflags,
        )
        output = "\n".join(filter(None, [completed.stdout, completed.stderr]))
        flags = _analyze_output(output)
        return ArchiveProbe(
            is_archive=completed.returncode == 0 or flags["archive_type"] is not None,
            archive_type=flags["archive_type"],
            needs_password=flags["needs_password"],
            wrong_password=flags["wrong_password"],
            missing_volume=flags["missing_volume"],
            reason=flags["reason"],
            raw_output=output,
        )

    def extract(
        self,
        archive_path: Path,
        destination: Path,
        password: str | None,
        is_cancelled: Callable[[], bool],
        log: Callable[[str], None],
    ) -> CommandResult:
        destination.mkdir(parents=True, exist_ok=True)
        command = [
            str(self.binary_path),
            "x",
            "-y",
            "-aoa",
            "-sccUTF-8",
            "-bso1",
            "-bse1",
            "-bsp1",
            f"-o{destination}",
            str(archive_path),
        ]
        if password is not None:
            command.append(f"-p{password}")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=self.creationflags,
        )
        lines: list[str] = []
        try:
            assert process.stdout is not None
            while True:
                if is_cancelled():
                    process.terminate()
                    process.wait(timeout=5)
                    return CommandResult(
                        success=False,
                        output="\n".join(lines),
                        return_code=-1,
                        reason="任务已取消",
                    )
                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    continue
                text = line.rstrip()
                if text:
                    lines.append(text)
                    log(text)
            return_code = process.wait()
        finally:
            if process.stdout is not None:
                process.stdout.close()

        output = "\n".join(lines)
        flags = _analyze_output(output)
        return CommandResult(
            success=return_code == 0,
            output=output,
            return_code=return_code,
            needs_password=flags["needs_password"],
            wrong_password=flags["wrong_password"],
            missing_volume=flags["missing_volume"],
            archive_type=flags["archive_type"],
            reason=flags["reason"],
        )


class RecursiveExtractor:
    def __init__(
        self,
        settings: AppSettings,
        settings_store: AppSettingsStore,
        tool: ArchiveTool | None = None,
    ) -> None:
        self.settings = settings
        self.settings_store = settings_store
        self.tool = tool or SevenZipTool()
        self._last_success_password: str | None = None

    def execute(
        self,
        job: ExtractionJob,
        *,
        log: Callable[[str], None],
        timeline: Callable[[str], None],
        request_password: Callable[[PasswordRequest], PasswordResponse | None],
        is_cancelled: Callable[[], bool],
    ) -> ExtractionResult:
        output_root = self._resolve_output_root(job)
        output_root.mkdir(parents=True, exist_ok=True)
        temp_root = Path(tempfile.mkdtemp(prefix="autounzip-"))
        self.settings_store.add_recent_input(str(job.input_path))
        result = ExtractionResult(final_output_dir=output_root)
        queue: list[tuple[ArchiveGroup, Path, int, bool]] = []
        processed: set[str] = set()
        root = job.input_path

        try:
            initial = discover_archives(root, self.settings, self.tool.probe)
            self._log_discovery(initial, log)
            if not initial.groups:
                raise RuntimeError("未找到可解压的压缩包、分卷或已配置的伪装后缀文件。")

            for group in initial.groups:
                queue.append((group, self._root_target(group, job, output_root), 0, False))

            while queue:
                if is_cancelled():
                    raise RuntimeError("任务已取消。")
                group, target_dir, layer, remove_source_after_success = queue.pop(0)
                fingerprint = self._fingerprint(group)
                if fingerprint in processed:
                    continue
                processed.add(fingerprint)
                if layer >= job.max_depth:
                    warning = f"已达到最大递归层级，跳过：{group.entry_path.name}"
                    log(warning)
                    result.warnings.append(warning)
                    continue

                timeline(f"第 {layer + 1} 层  ·  {group.entry_path.name}")
                log(
                    f"[候选] {group.entry_path} | 来源: {self._source_label(group)}"
                )
                stage_dir = temp_root / f"layer_{layer + 1}_{len(processed)}"
                success, password_source, warning = self._extract_group(
                    group=group,
                    layer=layer,
                    stage_dir=stage_dir,
                    target_dir=target_dir,
                    request_password=request_password,
                    is_cancelled=is_cancelled,
                    log=log,
                )
                if warning:
                    result.warnings.append(warning)
                if not success:
                    continue

                result.archives_extracted += 1
                result.layers_processed = max(result.layers_processed, layer + 1)
                if password_source:
                    result.password_sources.append(password_source)
                if remove_source_after_success:
                    self._cleanup_intermediate_archive(group, log)

                nested = discover_archives(target_dir, self.settings, self.tool.probe)
                self._log_discovery(nested, log)
                for nested_group in nested.groups:
                    nested_fingerprint = self._fingerprint(nested_group)
                    if nested_fingerprint in processed:
                        continue
                    queue.append(
                        (
                            nested_group,
                            self._nested_target(nested_group.entry_path),
                            layer + 1,
                            True,
                        )
                    )
        finally:
            if self.settings.cleanup_policy == "temporary_only":
                shutil.rmtree(temp_root, ignore_errors=True)

        return result

    def _extract_group(
        self,
        *,
        group: ArchiveGroup,
        layer: int,
        stage_dir: Path,
        target_dir: Path,
        request_password: Callable[[PasswordRequest], PasswordResponse | None],
        is_cancelled: Callable[[], bool],
        log: Callable[[str], None],
    ) -> tuple[bool, str | None, str | None]:
        log(f"[解压] 输出到 {target_dir}")
        result = self.tool.extract(group.entry_path, stage_dir, None, is_cancelled, log)
        if result.success:
            self._commit_stage_dir(stage_dir, target_dir)
            return True, "无密码", None
        if result.missing_volume:
            return False, None, f"分卷不完整，无法解压：{group.entry_path.name}"
        if not (result.needs_password or result.wrong_password):
            return False, None, f"解压失败：{group.entry_path.name} ({result.reason or '未知错误'})"

        password_candidates: list[tuple[str, str]] = []
        if self._last_success_password:
            password_candidates.append(("最近成功密码", self._last_success_password))
        for password in self.settings.password_library:
            password_candidates.append(("密码库", password))

        seen_passwords: set[str] = set()
        for source, password in password_candidates:
            if password in seen_passwords:
                continue
            seen_passwords.add(password)
            log(f"[密码] 尝试 {source}")
            stage_dir.mkdir(parents=True, exist_ok=True)
            shutil.rmtree(stage_dir, ignore_errors=True)
            stage_dir.mkdir(parents=True, exist_ok=True)
            attempt = self.tool.extract(group.entry_path, stage_dir, password, is_cancelled, log)
            if attempt.success:
                self._last_success_password = password
                self._commit_stage_dir(stage_dir, target_dir)
                return True, source, None
            if attempt.missing_volume:
                return False, None, f"分卷不完整，无法解压：{group.entry_path.name}"
            if not (attempt.needs_password or attempt.wrong_password):
                return False, None, f"解压失败：{group.entry_path.name} ({attempt.reason or '未知错误'})"

        manual_attempt = 0
        while manual_attempt < 3:
            manual_attempt += 1
            response = request_password(
                PasswordRequest(
                    archive_path=group.entry_path,
                    layer=layer + 1,
                    attempt_count=manual_attempt,
                    message="密码库未命中，请输入压缩包密码。",
                )
            )
            if response is None or response.cancel or not response.password:
                return False, None, f"用户取消输入密码：{group.entry_path.name}"

            password = response.password
            log("[密码] 尝试手动输入密码")
            shutil.rmtree(stage_dir, ignore_errors=True)
            stage_dir.mkdir(parents=True, exist_ok=True)
            attempt = self.tool.extract(group.entry_path, stage_dir, password, is_cancelled, log)
            if attempt.success:
                self._last_success_password = password
                self._commit_stage_dir(stage_dir, target_dir)
                if response.save_to_library:
                    self.settings = self.settings_store.add_password(password)
                    log("[密码] 手动密码已保存到密码库")
                return True, "手动输入", None
            if attempt.missing_volume:
                return False, None, f"分卷不完整，无法解压：{group.entry_path.name}"
            if not (attempt.needs_password or attempt.wrong_password):
                return False, None, f"解压失败：{group.entry_path.name} ({attempt.reason or '未知错误'})"

        return False, None, f"密码尝试失败：{group.entry_path.name}"

    def _resolve_output_root(self, job: ExtractionJob) -> Path:
        if job.output_dir is not None:
            return job.output_dir
        input_path = job.input_path
        if input_path.is_dir():
            return self._unique_directory(input_path.parent / f"{input_path.name}_unzipped")
        return self._unique_directory(input_path.parent / f"{input_path.stem}_unzipped")

    def _root_target(self, group: ArchiveGroup, job: ExtractionJob, output_root: Path) -> Path:
        if job.input_path.is_file():
            return output_root
        relative_parent = group.entry_path.parent.relative_to(job.input_path)
        base_dir = output_root / relative_parent
        return self._unique_directory(base_dir / f"{archive_display_stem(group)}_unzipped")

    def _nested_target(self, archive_path: Path) -> Path:
        # Nested archives are expanded back into their current directory so
        # wrapper archives do not leave *_unzipped nesting behind.
        return archive_path.parent

    def _unique_directory(self, path: Path) -> Path:
        if not path.exists():
            return path
        index = 2
        while True:
            candidate = path.with_name(f"{path.name}_{index}")
            if not candidate.exists():
                return candidate
            index += 1

    def _commit_stage_dir(self, stage_dir: Path, target_dir: Path) -> None:
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        if target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
            for item in stage_dir.iterdir():
                destination = target_dir / item.name
                if destination.exists():
                    destination = self._unique_path(destination)
                shutil.move(str(item), str(destination))
            shutil.rmtree(stage_dir, ignore_errors=True)
            return
        shutil.move(str(stage_dir), str(target_dir))

    def _unique_path(self, path: Path) -> Path:
        if not path.exists():
            return path
        index = 2
        while True:
            candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
            if not candidate.exists():
                return candidate
            index += 1

    def _fingerprint(self, group: ArchiveGroup) -> str:
        stat = group.entry_path.stat()
        return f"{group.entry_path.resolve()}::{stat.st_size}::{stat.st_mtime_ns}"

    def _cleanup_intermediate_archive(
        self, group: ArchiveGroup, log: Callable[[str], None]
    ) -> None:
        removed = 0
        for member_path in group.member_paths:
            if not member_path.exists():
                continue
            try:
                member_path.unlink()
                removed += 1
            except OSError as exc:
                log(f"[清理] 无法删除中间文件 {member_path}: {exc}")
        if removed == 1:
            log(f"[清理] 已删除中间压缩包 {group.entry_path.name}")
        elif removed > 1:
            log(
                f"[清理] 已删除中间压缩包及分卷 {group.entry_path.name} ({removed} 个文件)"
            )

    def _source_label(self, group: ArchiveGroup) -> str:
        if group.detection_source == "disguised_extension":
            return f"用户伪装后缀命中 {group.disguised_suffix}"
        if group.detection_source == "standard_extension":
            return "正常压缩包扩展名命中"
        return "分卷序列命中"

    def _log_discovery(self, discovery, log: Callable[[str], None]) -> None:
        for skipped in discovery.skipped:
            log(
                f"[跳过] {skipped.path} | 来源: {skipped.source} | 原因: {skipped.reason}"
            )


def _analyze_output(output: str) -> dict[str, object]:
    lower_output = output.lower()
    archive_type = None
    for line in output.splitlines():
        if line.startswith("Type = "):
            archive_type = line.split("=", 1)[1].strip()
            break

    wrong_password = any(
        token in lower_output
        for token in [
            "wrong password",
            "can not open encrypted archive. wrong password",
            "headers error",
        ]
    )
    needs_password = wrong_password or any(
        token in lower_output
        for token in [
            "enter password",
            "encrypted = +",
            "can not open encrypted archive",
            "data error in encrypted file. wrong password",
        ]
    )
    missing_volume = any(
        token in lower_output
        for token in [
            "unexpected end of archive",
            "cannot find volume",
            "can not find volume",
            "missing volume",
        ]
    )

    reason = None
    if missing_volume:
        reason = "缺少分卷"
    elif wrong_password or needs_password:
        reason = "需要密码或密码错误"
    elif "everything is ok" in lower_output:
        reason = "验证通过"
    elif "can not open file as archive" in lower_output or "is not archive" in lower_output:
        reason = "不是可识别的压缩包"

    return {
        "archive_type": archive_type,
        "wrong_password": wrong_password,
        "needs_password": needs_password,
        "missing_volume": missing_volume,
        "reason": reason,
    }
