# Publishing Downloads

Installers belong in **GitHub Releases**, not Git commits or Git LFS. Keep the original, versioned filenames and separate Apple Silicon from Intel. Keep iOS on the App Store. The English and Russian README pages point to the latest mirror release; older snapshot tags retain their downloads.

The **Sync DPN release** workflow in `DeeperNetwork/dpn-app` checks the official catalog every six hours at 00:17, 06:17, 12:17 and 18:17 UTC. It compares the installers with the latest published manifest and GitHub asset metadata. A change creates a fresh UTC-timestamped snapshot. A failed upload leaves the existing public release in place. A manual run also downloads the published installers and verifies their SHA-256 values.

This follows the multilingual README and multi-platform release patterns used by [RustDesk](https://github.com/rustdesk/rustdesk), [v2rayN](https://github.com/2dust/v2rayN), and [Outline](https://github.com/OutlineFoundation/outline-apps/releases). DPN mirrors the publisher's existing packages rather than building source code. Mirror-generated SHA-256 hashes detect corruption but are not a substitute for the publisher's digital signature.

## Prepare Locally

Requirements: Python 3.9+; GitHub CLI (`gh`) and repository write access only when publishing. No third-party Python dependencies are needed.

```sh
python3 -m unittest discover -s tests -v
python3 scripts/mirror_downloads.py --sync
```

The script reads the same public `appDownloads` API used by the official download page and downloads each platform's latest installers from `downloads.deeper.network`. It rejects missing platforms, unexpected source URLs, duplicate or unsafe filenames, and incomplete downloads. Both macOS architectures are required. Each file's byte size must match the official catalog.

Output is ignored by Git under `dist/downloads/`:

- Original Windows EXE, two macOS DMGs, Linux DEB, and Android APK.
- `SHA256SUMS.txt`: hashes for the downloaded installers.
- `download-manifest.json`: source URLs, platform versions, architectures, sizes, and hashes.
- `RELEASE_NOTES.md`: English/Russian notes with per-platform download links.

Choose a fresh snapshot tag for each publication. Different platforms may have different full build versions, so the snapshot tag is not an app version. The Android architecture field and filename are copied from upstream, not independently certified.

## Publish

For an immediate sync, run **Sync DPN release** from Actions on `main`. To publish a specific snapshot locally, authenticate `gh` with write access to the chosen repository and run:

```sh
python3 scripts/mirror_downloads.py \
  --tag downloads-YYYY-MM-DD-HHMMSSZ \
  --repository DeeperNetwork/dpn-app \
  --target main \
  --publish
```

This command downloads a fresh snapshot, creates a **draft**, uploads the installers and two integrity files, compares GitHub's asset sizes and SHA-256 digests with the local files, then publishes the release as latest. A failed upload or verification leaves the draft unpublished. Existing releases are never overwritten. Inspect a failed draft before manually removing it or retrying with a new tag.

For a fork, set `--repository` to that fork and update both README release links. Do not present a personal mirror as the official release repository.

The installation packages are not executed, edited, repackaged, or re-signed. The official catalog currently has no upstream SHA-256 values; the generated manifest records the exact bytes downloaded over HTTPS.
