---
applyTo: "apps/**/*.ts,apps/**/*.vue,apps/**/*.js,apps/**/*.json"
---
Use Node only for build/dev tooling. Use npm workspaces from `apps/package.json`. Keep dependencies pinned deliberately. Vue owns application state. jQuery UI is compatibility-only for draggable/resizable outer hosts and must not mutate Vue-managed descendants. Never place provider secrets or Mixpanel service credentials in browser code.
