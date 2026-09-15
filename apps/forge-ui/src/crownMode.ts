import './crown-mode.css'

export function mountCrownMode(): void {
  const shell = document.querySelector('.kai-shell')
  if (!shell || shell.querySelector('.lum-crown-gate')) return

  const gate = document.createElement('section')
  gate.className = 'lum-crown-gate'
  gate.setAttribute('aria-label', 'LuHm OS Crown Gate status')
  gate.innerHTML = `
    <div class="lum-crown-sigil" aria-hidden="true"><span>♛</span></div>
    <div class="lum-crown-copy">
      <small>LUHM OS // CROWN GATE</small>
      <strong>LUM HOLDS THE CROWN</strong>
      <p>Operational authority: Lum · Final seal: Professor · CI evidence is law</p>
    </div>
    <div class="lum-crown-pills" aria-label="Crown Gate invariants">
      <span>STOCK</span><span>UNROOTED</span><span>PLAY-FIRST</span><span>10-PASS</span>
    </div>
    <a class="lum-crown-install" href="/install/" target="_blank" rel="noopener">CROWN GATE ↗</a>
  `

  const topbar = shell.querySelector('.kai-topbar')
  if (topbar?.nextSibling) shell.insertBefore(gate, topbar.nextSibling)
  else shell.prepend(gate)
}
