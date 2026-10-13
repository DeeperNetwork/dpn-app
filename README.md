# DPN: Beyond VPN

**English** | [Русский](README.ru.md)

**DPN** is a privacy-oriented app from [Deeper Network](https://www.deeper.network/) that combines app-aware routing, selectable encrypted tunnels, and network-level filtering in one device-level application.

[GitHub Download Mirror](https://github.com/tiger-zsh/dpn-app/releases/latest) | [Official Download Page](https://dpn.deeper.network/download) | [How DPN Works](https://dpn.deeper.network/how-dpn-works) | [FAQ](https://dpn.deeper.network/faq)

> **7-day free trial code:** `ZJXYY8NB`

![DPN: Smart Route](output/imagegen/dpn-smart-route.svg)

## Why DPN

Traditional full-tunnel VPNs send included traffic through a single exit. DPN gives you more control over how individual apps and connections are routed.

- **App Relocator** assigns supported apps to selected country tunnels while other traffic can stay direct.
- **Multi-tunnel Smart Route** keeps multiple selected tunnels available so supported apps can use different routes at the same time.
- **Flexible routing modes** let you choose between app-aware routing, a single full tunnel, or a direct connection.
- **Deeper Filtering Engine** applies DNS/IP rules across supported traffic, with optional HTTPS filtering where the platform supports it.

## Routing Modes

| Mode | How it works |
| --- | --- |
| **Smart Route** | Applies app-aware rules so supported apps can use assigned tunnels while other traffic stays direct or follows another available route. |
| **Full Route** | Sends traffic through one selected exit route. |
| **Direct Route** | Keeps ordinary traffic direct while retaining supported filtering controls. |

## Download DPN

Open the [latest GitHub mirror release](https://github.com/tiger-zsh/dpn-app/releases/latest) and choose your installer under **Assets**. Older mirrored packages remain available in [all mirror releases](https://github.com/tiger-zsh/dpn-app/releases). The original installers are also available on the [official download page](https://dpn.deeper.network/download).

The GitHub download mirror is maintained by [tiger-zsh](https://github.com/tiger-zsh/dpn-app), separately from the [official repository](https://github.com/DeeperNetwork/dpn-app). It copies the official installers without modification; it is not an official Deeper Network release channel.

| Platform | Architecture | Installer to choose |
| --- | --- | --- |
| Windows | x86-64 | `DPN-<version>-windows-x86-64.exe` |
| macOS | Apple Silicon (M-series) | `DPN-<version>-macos-arm-64.dmg` |
| macOS | Intel | `DPN-<version>-macos-x86-64.dmg` |
| Linux | x86-64, Debian/Ubuntu | `DPN-<version>-linux-x86-64.deb` |
| Android | Official APK | `DPN-<version>-android-x64.apk` |
| iOS | iPhone/iPad | [Apple App Store](https://apps.apple.com/us/app/dpn-beyond-vpn/id6748636811) |

Versions can differ by platform. The Android filename follows the publisher's naming; it is not a statement of supported CPU architectures. iOS is distributed through the App Store, not as a GitHub installer.

### Verify Your Download

Each mirrored release includes `SHA256SUMS.txt` and `download-manifest.json`, listing the original download URLs, versions, file sizes, and SHA-256 hashes. The installers are mirrored without modification or re-signing. Checksums detect changed or incomplete downloads; they are not an independent publisher signature.

Download `SHA256SUMS.txt` alongside your chosen installer. On macOS or Linux, calculate its hash with `shasum -a 256 <installer-file>` or `sha256sum <installer-file>` and compare it with the matching entry. In Windows PowerShell, use `Get-FileHash .\<installer-file> -Algorithm SHA256`.

## Filtering Notes

Routing and filtering are separate controls. DNS/IP filtering applies configured domain and IP rules before supported connections are made. HTTPS filtering requires the Deeper Network root certificate, and its coverage depends on the operating system. On Android, HTTPS filtering applies in supported web browsers and does not apply inside other apps.

With the right filtering rules enabled, supported traffic can also avoid many common advertising and tracking endpoints. Depending on the platform and the app's connection paths, this may help reduce interruptions in services such as the YouTube iOS app and Spotify, while results can vary as those services change their delivery infrastructure.

![DPN: Ad filtering and safer connections](output/imagegen/dpn-filtering-protection.svg)

## Inside the App

Explore the home dashboard, per-app routing, and network protection in these iOS App Store previews. Interface and available controls vary by platform and version.

![DPN iOS previews: home dashboard, Smart Route, and DNS/IP filtering](output/product/dpn-ios-preview.jpg)

## DPN and Deeper Connect

DPN is an official Deeper Network software product that runs directly on an individual device. It does not require Deeper Connect hardware. Deeper Connect is a separate product designed for network-level deployment.

## Official Resources

- [DPN Download](https://dpn.deeper.network/download)
- [How DPN Works](https://dpn.deeper.network/how-dpn-works)
- [Frequently Asked Questions](https://dpn.deeper.network/faq)
- [Privacy Policy](https://dpn.deeper.network/privacy-policy)
- [Terms of Use](https://dpn.deeper.network/terms-of-use)
- [Deeper Network](https://www.deeper.network/)

## About This Repository

This repository is the public distribution home for DPN release packages and release notes. It does not contain the DPN source code. Use of DPN is subject to the [Terms of Use](https://dpn.deeper.network/terms-of-use).

Maintainers: see [Publishing Downloads](docs/publishing-downloads.md) for the official-source mirror and release workflow.
