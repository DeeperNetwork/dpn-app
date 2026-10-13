import copy
import hashlib
import io
import tempfile
import unittest
import json
import subprocess
from email.message import Message
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.mirror_downloads import (
    DOWNLOAD_ORIGIN, download, official_assets, publish, release_notes, verify_uploaded,
)


def catalog():
    result = {"platforms": {}}
    for platform, filename_platform, extension, arches in [
        ("windows", "windows", ".exe", ["x86-64"]),
        ("mac", "macos", ".dmg", ["x86-64", "arm-64"]),
        ("linux", "linux", ".deb", ["x86-64"]),
        ("android", "android", ".apk", ["x64"]),
    ]:
        version = "3.0.8.260924" if platform == "mac" else "3.0.8.260923"
        assets = []
        for arch in arches:
            name = "DPN-{}-{}-{}{}".format(version, filename_platform, arch, extension)
            assets.append({"platform": platform, "version": version, "arch": arch,
                           "fileName": name, "url": DOWNLOAD_ORIGIN + name, "size": 4})
        result["platforms"][platform] = {"latestVersion": version, "latest": assets}
    return result


class Response(io.BytesIO):
    def __init__(self, data, url, content_type="application/octet-stream"):
        super().__init__(data)
        self.url = url
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def geturl(self):
        return self.url


class CatalogTests(unittest.TestCase):
    def test_all_platforms_and_independent_versions(self):
        assets = official_assets(catalog())
        self.assertEqual(len(assets), 5)
        self.assertEqual(len({asset["version"] for asset in assets}), 2)

    def test_invalid_catalog_structure_is_rejected(self):
        for data in [None, [], {}, {"platforms": []}, {"platforms": {"windows": None}},
                     {"platforms": {"windows": {"latestVersion": "1.0", "latest": [None]}}}]:
            with self.subTest(catalog=data):
                with self.assertRaises(ValueError):
                    official_assets(data)

    def test_invalid_metadata_is_rejected(self):
        for field, value in [
            ("fileName", "../DPN-escape.exe"),
            ("url", "https://example.com/DPN-installer.exe"),
            ("size", 0), ("size", True), ("size", "4"),
            ("version", "0.0.0"), ("platform", "linux"),
            ("arch", "x64|injected"),
            ("fileName", None), ("arch", None), ("version", None),
        ]:
            with self.subTest(field=field, value=value):
                data = catalog()
                data["platforms"]["windows"]["latest"][0][field] = value
                with self.assertRaises(ValueError):
                    official_assets(data)

    def test_wrong_extension_is_rejected(self):
        data = catalog()
        asset = data["platforms"]["windows"]["latest"][0]
        asset["fileName"] = "DPN-3.0.8-windows.exe.html"
        asset["url"] = DOWNLOAD_ORIGIN + asset["fileName"]
        with self.assertRaises(ValueError):
            official_assets(data)

    def test_duplicates_are_rejected(self):
        data = catalog()
        entry = data["platforms"]["mac"]["latest"]
        entry.append(copy.deepcopy(entry[0]))
        with self.assertRaises(ValueError):
            official_assets(data)

    def test_missing_platform_is_rejected(self):
        data = catalog()
        del data["platforms"]["android"]
        with self.assertRaises(ValueError):
            official_assets(data)

    def test_both_mac_architectures_required(self):
        data = catalog()
        data["platforms"]["mac"]["latest"].pop()
        with self.assertRaises(ValueError):
            official_assets(data)

    def test_bilingual_notes_link_to_original_names(self):
        assets = official_assets(catalog())
        notes = release_notes(assets, "DeeperNetwork/dpn-app", "downloads-2026-10-02")
        self.assertIn("Загрузка DPN", notes)
        for asset in assets:
            self.assertIn("/releases/download/downloads-2026-10-02/" + asset["fileName"], notes)
        self.assertIn("Apple Silicon", notes)
        self.assertIn("Intel", notes)
        self.assertIn("apps.apple.com", notes)


class DownloadTests(unittest.TestCase):
    def test_download_preserves_bytes_and_calculates_sha256(self):
        asset = official_assets(catalog())[0]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with patch("scripts.mirror_downloads.urlopen", return_value=Response(b"MZ00", asset["url"])):
                record = download(asset, output)
            self.assertEqual((output / asset["fileName"]).read_bytes(), b"MZ00")
            self.assertEqual(record["sha256"], hashlib.sha256(b"MZ00").hexdigest())
            self.assertEqual(len(list(output.iterdir())), 1)

    def test_failed_download_does_not_replace_existing_file(self):
        asset = official_assets(catalog())[0]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            path = output / asset["fileName"]
            path.write_bytes(b"old")
            with patch("scripts.mirror_downloads.urlopen", return_value=Response(b"MZ", asset["url"])):
                with self.assertRaises(ValueError):
                    download(asset, output)
            self.assertEqual(path.read_bytes(), b"old")
            self.assertEqual(list(output.iterdir()), [path])

    def test_html_response_is_rejected(self):
        asset = official_assets(catalog())[0]
        with tempfile.TemporaryDirectory() as directory:
            with patch("scripts.mirror_downloads.urlopen", return_value=Response(b"oops", asset["url"], "text/html")):
                with self.assertRaises(ValueError):
                    download(asset, Path(directory))
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_external_redirect_is_rejected(self):
        asset = official_assets(catalog())[0]
        with tempfile.TemporaryDirectory() as directory:
            with patch("scripts.mirror_downloads.urlopen", return_value=Response(b"MZ00", "https://example.com/package")):
                with self.assertRaises(ValueError):
                    download(asset, Path(directory))

    def test_http_redirect_is_rejected(self):
        asset = official_assets(catalog())[0]
        with tempfile.TemporaryDirectory() as directory:
            with patch("scripts.mirror_downloads.urlopen", return_value=Response(b"MZ00", asset["url"].replace("https:", "http:"))):
                with self.assertRaises(ValueError):
                    download(asset, Path(directory))

    def test_oversized_response_is_rejected(self):
        asset = official_assets(catalog())[0]
        with tempfile.TemporaryDirectory() as directory:
            with patch("scripts.mirror_downloads.urlopen", return_value=Response(b"MZ000", asset["url"])):
                with self.assertRaises(ValueError):
                    download(asset, Path(directory))
            self.assertEqual(list(Path(directory).iterdir()), [])


class PublishTests(unittest.TestCase):
    def test_only_verified_uploads_are_published(self):
        args = SimpleNamespace(tag="downloads-test", repository="owner/repo", target="main")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "DPN.exe"
            path.write_bytes(b"MZ00")
            metadata = {"name": path.name, "size": 4,
                        "digest": "sha256:" + hashlib.sha256(b"MZ00").hexdigest()}
            with patch("scripts.mirror_downloads.gh", side_effect=["", "", json.dumps({"databaseId": 42}), json.dumps({"assets": [metadata]}), ""]) as cli:
                publish(args, [path], Path(directory) / "notes.md")
            calls = [call.args for call in cli.call_args_list]
            self.assertEqual(calls[0][:2], ("release", "create"))
            self.assertIn("--draft", calls[0])
            self.assertEqual(calls[1][:2], ("release", "upload"))
            self.assertEqual(calls[2][:2], ("release", "view"))
            self.assertEqual(calls[3], ("api", "repos/owner/repo/releases/42"))
            self.assertEqual(calls[4][:2], ("release", "edit"))
            self.assertIn("--draft=false", calls[4])

    def test_failed_upload_or_verification_leaves_draft(self):
        args = SimpleNamespace(tag="downloads-test", repository="owner/repo", target="main")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "DPN.exe"
            path.write_bytes(b"MZ00")
            for outcomes, exception in [
                (["", subprocess.CalledProcessError(1, "gh")], subprocess.CalledProcessError),
                (["", "", json.dumps({"databaseId": 42}), json.dumps({"assets": []})], ValueError),
            ]:
                with self.subTest(outcomes=outcomes):
                    with patch("scripts.mirror_downloads.gh", side_effect=outcomes) as cli:
                        with self.assertRaises(exception):
                            publish(args, [path], Path(directory) / "notes.md")
                    self.assertFalse(any(call.args[:2] == ("release", "edit") for call in cli.call_args_list))

    def test_uploaded_digest_and_size_must_match(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "DPN.exe"
            path.write_bytes(b"MZ00")
            metadata = {"name": path.name, "size": 4,
                        "digest": "sha256:" + hashlib.sha256(b"MZ00").hexdigest()}
            verify_uploaded([metadata], [path])
            for field, value in [("size", 3), ("digest", "sha256:wrong"), ("digest", None)]:
                with self.subTest(field=field):
                    bad = dict(metadata, **{field: value})
                    with self.assertRaises(ValueError):
                        verify_uploaded([bad], [path])

    def test_missing_or_extra_upload_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "DPN.exe"
            path.write_bytes(b"MZ00")
            with self.assertRaises(ValueError):
                verify_uploaded([], [path])
            with self.assertRaises(ValueError):
                verify_uploaded([{"name": "unexpected.exe"}], [path])


if __name__ == "__main__":
    unittest.main()
