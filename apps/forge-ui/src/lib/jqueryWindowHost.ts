import $ from 'jquery'
import 'jquery-ui/ui/widgets/draggable'
import 'jquery-ui/ui/widgets/resizable'

export type WindowHostOptions = {
  handle?: string
  containment?: string | HTMLElement
  minWidth?: number
  minHeight?: number
}

/**
 * Compatibility seam only. Vue owns state and content; jQuery UI may move/resize
 * the outer panel element but must not mutate Vue-managed descendants.
 */
export function attachLegacyWindowHost(el: HTMLElement, options: WindowHostOptions = {}) {
  const host = $(el)
  host.draggable({
    handle: options.handle ?? '[data-window-handle]',
    containment: options.containment ?? 'parent',
  })
  host.resizable({
    minWidth: options.minWidth ?? 320,
    minHeight: options.minHeight ?? 220,
    containment: options.containment ?? 'parent',
  })

  return () => {
    if (host.hasClass('ui-draggable')) host.draggable('destroy')
    if (host.hasClass('ui-resizable')) host.resizable('destroy')
  }
}
