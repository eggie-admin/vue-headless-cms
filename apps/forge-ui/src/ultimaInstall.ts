const ULTIMA_INSTALL_URL = 'https://drive.google.com/file/d/1VdIHSmliBscT4UBa_1BCXKEO0a1baRCr/view?usp=drivesdk'
const ULTIMA_APK_SHA256 = '72b56eb9086ea9a5bca99fc42e85aefc2094b8a1940a60aa3d5a7e8c05431f5b'

function mountUltimaInstall(): boolean {
  const artifacts = document.querySelector<HTMLElement>('#artifacts .kai-save-grid')
  if (!artifacts) return false
  if (document.querySelector('[data-luhmos-ultima-install]')) return true

  const card = document.createElement('article')
  card.className = 'kai-card'
  card.dataset.luhmosUltimaInstall = 'true'
  card.innerHTML = `
    <p class="eyebrow">ULTIMA / TESTING</p>
    <h3>LuHm OS installer</h3>
    <p>Verified API 36 · ARM64 · 16 KiB testing APK from the Source of Truth.</p>
    <a class="kai-btn" href="${ULTIMA_INSTALL_URL}" target="_blank" rel="noopener noreferrer">Install / reinstall from Google Drive</a>
    <small>SHA-256 ${ULTIMA_APK_SHA256.slice(0, 16)}… · ephemeral CI signer</small>
  `
  artifacts.prepend(card)
  return true
}

function bootUltimaInstall() {
  if (mountUltimaInstall()) return
  const observer = new MutationObserver(() => {
    if (mountUltimaInstall()) observer.disconnect()
  })
  observer.observe(document.documentElement, { childList: true, subtree: true })
  window.setTimeout(() => observer.disconnect(), 10_000)
}

document.addEventListener('DOMContentLoaded', bootUltimaInstall, { once: true })
