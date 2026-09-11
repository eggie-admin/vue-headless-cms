const ULTIMA_INSTALL_URL = 'https://drive.google.com/file/d/1VdIHSmliBscT4UBa_1BCXKEO0a1baRCr/view?usp=drivesdk'

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
    <small>Source-of-Truth artifact · ephemeral CI signer · hash recorded in provenance</small>
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
