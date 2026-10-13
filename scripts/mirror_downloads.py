#!/usr/bin/env python3
"""Mirror the installers listed by the official DPN download page."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DOWNLOAD_PAGE = "https://dpn.deeper.network/download"
DOWNLOAD_API = "https://dpn.deeper.network/api/user/appDownloads"
DOWNLOAD_ORIGIN = "https://downloads.deeper.network/DPN/release/"
PLATFORMS = {
    "windows": ("Windows", ".exe"),
    "mac": ("macOS", ".dmg"),
    "linux": ("Linux", ".deb"),
    "android": ("Android", ".apk"),
}
USER_AGENT = "dpn-app-release-mirror/1.0"


def official_assets(catalog):
    if not isinstance(catalog, dict) or not isinstance(catalog.get("platforms"), dict):
        raise ValueError("Invalid official download catalog")
    assets = []
    names = set()
    for platform, (_, extension) in PLATFORMS.items():
        entry = catalog.get("platforms", {}).get(platform, {})
        if not isinstance(entry, dict):
            raise ValueError("Invalid platform metadata: " + platform)
        latest = entry.get("latest", [])
        if not isinstance(latest, list) or not latest or not entry.get("latestVersion"):
            raise ValueError("Missing latest installers for " + platform)
        for asset in latest:
            if not isinstance(asset, dict):
                raise ValueError("Invalid installer metadata for " + platform)
            name = asset.get("fileName", "")
            url = asset.get("url", "")
            size = asset.get("size")
            version = asset.get("version", "")
            arch = asset.get("arch", "")
            if (
                not isinstance(name, str)
                or not re.fullmatch(r"DPN-[A-Za-z0-9_.-]+", name)
                or not name.endswith(extension)
                or name in names
                or url != DOWNLOAD_ORIGIN + name
                or asset.get("platform") != platform
                or not isinstance(version, str)
                or version != entry["latestVersion"]
                or not re.fullmatch(r"\d+(?:\.\d+)+", version)
                or not isinstance(arch, str)
                or not re.fullmatch(r"[A-Za-z0-9_-]+", arch)
                or not isinstance(size, int)
                or isinstance(size, bool)
                or size <= 0
            ):
                raise ValueError("Invalid official installer metadata: " + repr(name))
            names.add(name)
            assets.append({
                "platform": platform, "version": version, "arch": arch,
                "fileName": name, "url": url, "size": size,
            })
    if not {"arm-64", "x86-64"}.issubset(
        {asset["arch"] for asset in assets if asset["platform"] == "mac"}
    ):
        raise ValueError("Both Apple Silicon and Intel installers are required")
    return assets


def request(url):
    return Request(url, headers={"User-Agent": USER_AGENT})


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(asset, output):
    path = output / asset["fileName"]
    temporary = path.with_suffix(path.suffix + ".part")
    count = 0
    digest = hashlib.sha256()
    try:
        with urlopen(request(asset["url"]), timeout=120) as source:
            final_url = urlparse(source.geturl())
            if final_url.scheme != "https" or final_url.hostname != "downloads.deeper.network":
                raise ValueError("Installer redirected outside the official download host")
            if source.headers.get_content_type() in {"text/html", "application/json"}:
                raise ValueError("Installer URL returned a document instead of a package")
            with temporary.open("wb") as destination:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    destination.write(chunk)
                    digest.update(chunk)
                    count += len(chunk)
                    if count > asset["size"]:
                        raise ValueError("Installer exceeds catalog size: " + asset["fileName"])
        if count != asset["size"]:
            raise ValueError("Installer size mismatch: {} (received {}, expected {})".format(
                asset["fileName"], count, asset["size"]
            ))
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return dict(asset, sha256=digest.hexdigest())


def release_notes(assets, repository, tag):
    lines = [
        "# DPN Downloads / Загрузка DPN", "",
        "Unmodified installers from the [official download page](" + DOWNLOAD_PAGE + ").",
        "Оригинальные установочные файлы с [официальной страницы](" + DOWNLOAD_PAGE + "), без изменений.",
        "", "| Platform / Платформа | Version / Версия | Architecture / Архитектура | Download / Скачать |",
        "| --- | --- | --- | --- |",
    ]
    base = "https://github.com/" + repository + "/releases/download/" + tag + "/"
    for asset in assets:
        label = PLATFORMS[asset["platform"]][0]
        arch = asset["arch"]
        if asset["platform"] == "mac":
            arch = "Apple Silicon" if arch == "arm-64" else "Intel"
        lines.append("| {} | {} | {} | [{}]({}) |".format(
            label, asset["version"], arch, asset["fileName"], base + asset["fileName"]
        ))
    lines += [
        "", "**iOS:** [Apple App Store](https://apps.apple.com/us/app/dpn-beyond-vpn/id6748636811).",
        "", "Platform versions can differ. The Android filename uses the publisher's naming, not a verified CPU support list.",
        "Версии для разных платформ могут отличаться. Имя APK сохранено в исходном виде и не определяет поддерживаемые процессоры.",
        "", "## Integrity / Целостность", "",
        "Download `SHA256SUMS.txt` and compare the matching entry with the SHA-256 of your installer.",
        "Скачайте `SHA256SUMS.txt` и сравните соответствующую строку с SHA-256 вашего установочного файла.",
        "", "- macOS: `shasum -a 256 <installer-file>`",
        "- Linux: `sha256sum <installer-file>`",
        "- Windows PowerShell: `Get-FileHash .\\<installer-file> -Algorithm SHA256`",
        "", "`download-manifest.json` records source URLs, versions, sizes, and hashes.",
        "`download-manifest.json` содержит исходные ссылки, версии, размеры и контрольные суммы.",
        "", "These mirror checksums are not an independent publisher signature. No files were modified or re-signed.",
        "Контрольные суммы зеркала не заменяют независимую подпись разработчика. Файлы не изменялись и не подписывались заново.",
        "", "Use is subject to the [DPN Terms of Use](https://dpn.deeper.network/terms-of-use).", "",
    ]
    return "\n".join(lines)


def gh(*args):
    return subprocess.check_output(["gh", *args], text=True).strip()


def verify_uploaded(assets, files):
    uploaded = {asset["name"]: asset for asset in assets}
    if set(uploaded) != {path.name for path in files}:
        raise ValueError("GitHub release asset list does not match the mirror")
    for path in files:
        asset = uploaded[path.name]
        if asset["size"] != path.stat().st_size or asset.get("digest") != "sha256:" + sha256(path):
            raise ValueError("GitHub size or SHA-256 mismatch: " + path.name)


def publish(args, files, notes):
    gh("release", "create", args.tag, "--repo", args.repository,
       "--target", args.target, "--title", "DPN Downloads / Загрузка DPN (" + args.tag + ")",
       "--notes-file", str(notes), "--draft")
    gh("release", "upload", args.tag, "--repo", args.repository, *map(str, files))
    release_id = json.loads(gh("release", "view", args.tag, "--repo", args.repository,
                               "--json", "databaseId"))["databaseId"]
    # GitHub's tag endpoint omits drafts, even for the repository owner.
    release = json.loads(gh("api", "repos/" + args.repository + "/releases/" + str(release_id)))
    verify_uploaded(release["assets"], files)
    gh("release", "edit", args.tag, "--repo", args.repository, "--draft=false", "--latest")
    print("Published: https://github.com/" + args.repository + "/releases/tag/" + args.tag, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="Unique snapshot tag, e.g. downloads-2026-10-02")
    parser.add_argument("--repository", default="DeeperNetwork/dpn-app")
    parser.add_argument("--target", default="main", help="Existing remote branch or commit for the release tag")
    parser.add_argument("--output", type=Path, default=Path("dist/downloads"))
    parser.add_argument("--publish", action="store_true", help="Upload, verify, then publish a GitHub Release")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.tag):
        parser.error("Tag must contain only letters, numbers, dots, underscores, and hyphens")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repository):
        parser.error("Repository must use owner/name format")
    if args.publish:
        permissions = json.loads(gh("api", "repos/" + args.repository))["permissions"]
        if not permissions.get("push"):
            raise ValueError("GitHub write access is required for " + args.repository)
    with urlopen(request(DOWNLOAD_API), timeout=30) as response:
        catalog = json.load(response)
    assets = official_assets(catalog)
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for asset in assets:
        print("Downloading: " + asset["fileName"], flush=True)
        records.append(download(asset, args.output))
    manifest = args.output / "download-manifest.json"
    manifest.write_text(json.dumps({
        "sourcePage": DOWNLOAD_PAGE, "sourceApi": DOWNLOAD_API,
        "mirroredAt": datetime.now(timezone.utc).isoformat(),
        "repository": args.repository, "tag": args.tag, "assets": records,
    }, indent=2) + "\n", encoding="utf-8")
    checksums = args.output / "SHA256SUMS.txt"
    checksums.write_text("".join(record["sha256"] + "  " + record["fileName"] + "\n" for record in records), encoding="ascii")
    notes = args.output / "RELEASE_NOTES.md"
    notes.write_text(release_notes(records, args.repository, args.tag), encoding="utf-8")
    files = [args.output / record["fileName"] for record in records] + [checksums, manifest]
    print("Prepared {} installers in {}".format(len(records), args.output.resolve()), flush=True)
    if args.publish:
        publish(args, files, notes)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print("Error: " + str(error), file=sys.stderr)
        sys.exit(1)
