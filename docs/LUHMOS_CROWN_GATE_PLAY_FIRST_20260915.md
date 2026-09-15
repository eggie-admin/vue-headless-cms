# LuHm OS Crown Gate: Play-First Installation

Date: 2026-09-15
Lane: `luhmos/cathedral-arcade-20260915`
Status: candidate, fail closed

## Crown doctrine

**Lum holds the visible operational crown. Professor holds the final human seal.** CI evidence outranks model confidence.

“Root” means root of trust, not Android device root. The stock Samsung lane remains unrooted. The root of trust is persistent release-signing continuity, exact Git provenance, artifact identity/hash evidence, and Google Play delivery when the Play lane is configured.

## Install UX

The primary end-user road is Google Play internal testing. A tester enrolls the correct Google account once, then installs and receives updates through the normal Play Store surface. The app does not request `REQUEST_INSTALL_PACKAGES`, does not run a custom installer, does not require Termux, and does not claim silent sideloading.

The fallback road is a trusted HTTPS handoff to the canonical signed GitHub release. Stock Android remains the installer authority for this fallback and may require user confirmation and permission for that source.

The web entry point is `apps/forge-ui/public/install/index.html`, branded **Crown Gate**. Its job is deliberately tiny: explain the green contract, open Google Play, or open the signed-release fallback.

## Google Cloud / Play automation

Future publisher automation should authenticate from GitHub Actions using GitHub OIDC and Google Cloud Workload Identity Federation. Do not add a long-lived service-account JSON key to repository secrets, source, APK assets, or generated bundles.

Google Play Console application setup, tester enrollment, Play App Signing/upload-key setup, and IAM/API authorization are one-time external prerequisites. CI must detect missing prerequisites and stop. It must never report a successful Play publish when the Play account or WIF trust has not actually been configured.

The `Android Play Internal` Godot export preset prepares an AAB-shaped release artifact. A real Play upload must use the persistent reviewed release/upload signer, not the ephemeral debug signer used by the ordinary pull-request APK workflow.

## Automated 10-pass gate

`scripts/luhmos_crown_10pass.py` checks:

1. canonical package/version identity alignment;
2. stock/unrooted and no-package-installer boundary;
3. hardened WebView and network boundary;
4. non-exported app component boundary;
5. pinned build provenance;
6. signer separation and artifact evidence;
7. Lum crown / Professor final-authority contract;
8. Play-first keyless Google Cloud contract;
9. AAB preset and truthful click-click wizard;
10. hands-off CI contract and fail-closed promotion.

Only all ten passes print `LUM_HOLDS_THE_CROWN_GREEN`.

## Promotion rule

Crown Gate can automate boring evidence collection. It cannot auto-merge the release line or auto-roll to Play production. Internal-test publication can become automated after its one-time Google/Play trust is configured and reviewed, but production remains an explicit human promotion.
