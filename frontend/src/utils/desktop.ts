import type { Router } from 'vue-router'

import { useAuthStore } from '@/store/auth'
import { useWorkspaceStore, type WorkspaceMode } from '@/store/workspace'
import { clearSession as clearWebSession } from '@/api/authSession'
import { pinia } from '@/store/pinia'

export interface DesktopSessionUser {
  userId: number
  username: string
  displayName: string
  roles: string[]
}

export interface DesktopSessionPayload {
  accountId: string
  accessToken: string
  user: DesktopSessionUser
}

export interface DesktopRoutePayload {
  path: string
}

export interface DesktopWorkspacePayload {
  workspaceKey: 'admin' | 'business'
}

export interface DesktopStateChangedPayload {
  currentRoute: string
  workspaceKey: 'admin' | 'business' | ''
  userId: number | null
}

function getDesktopApi() {
  if (typeof window === 'undefined') {
    return null
  }

  return window.desktopApp ?? null
}

export function isDesktopShell(): boolean {
  if (typeof window === 'undefined') {
    return false
  }

  try {
    if (window.parent !== window) {
      return false
    }
  } catch {
    return false
  }

  if (getDesktopApi()?.isDesktopShell) {
    return true
  }

  return false
}

export function isDesktopEmbedded(): boolean {
  if (typeof window === 'undefined') {
    return false
  }

  if (getDesktopApi()?.isDesktopShell) {
    return true
  }

  try {
    return window.parent !== window
  } catch {
    return false
  }
}

export function syncDesktopModeAttribute(): void {
  if (typeof document === 'undefined') {
    return
  }

  if (isDesktopEmbedded()) {
    document.body.dataset.desktopShell = 'true'
    return
  }

  delete document.body.dataset.desktopShell
}

export async function notifyDesktopStateChanged(payload: DesktopStateChangedPayload): Promise<void> {
  await getDesktopApi()?.notifyWebState?.(payload)
}

export function registerDesktopBridge(bridge: {
  applySession: (payload: DesktopSessionPayload) => Promise<void> | void
  clearSession: () => Promise<void> | void
  navigateTo: (payload: DesktopRoutePayload) => Promise<void> | void
  setWorkspace: (payload: DesktopWorkspacePayload) => Promise<void> | void
  getCurrentRoute: () => string
  getCurrentUser: () => DesktopSessionUser | null
}) {
  if (typeof window === 'undefined') {
    return
  }

  window.desktopBridge = bridge
}

function normalizeWorkspaceKey(value: 'admin' | 'business'): WorkspaceMode {
  return value
}

export function installDesktopBridge(router: Router): void {
  const auth = useAuthStore(pinia)
  const workspace = useWorkspaceStore(pinia)

  registerDesktopBridge({
    async applySession(payload) {
      auth.setToken(payload.accessToken)
      auth.setUser({
        id: payload.user.userId,
        username: payload.user.username,
        real_name: payload.user.displayName,
        roles: payload.user.roles,
      })
      const resolvedWorkspace = workspace.resolveDefaultWorkspace(payload.user.roles)
      if (resolvedWorkspace) {
        workspace.setWorkspace(resolvedWorkspace)
      } else {
        workspace.clearWorkspace()
      }
      await notifyDesktopStateChanged({
        currentRoute: router.currentRoute.value.fullPath,
        workspaceKey: resolvedWorkspace ?? workspace.currentWorkspace ?? '',
        userId: payload.user.userId,
      })
    },
    async clearSession() {
      await clearWebSession({ silent: true })
      await router.replace('/login')
    },
    async navigateTo(payload) {
      await router.replace(payload.path)
    },
    async setWorkspace(payload) {
      const nextWorkspace = normalizeWorkspaceKey(payload.workspaceKey)
      workspace.setWorkspace(nextWorkspace)
    },
    getCurrentRoute() {
      return router.currentRoute.value.fullPath
    },
    getCurrentUser() {
      if (!auth.user) {
        return null
      }

      return {
        userId: auth.user.id,
        username: auth.user.username,
        displayName: auth.user.real_name || auth.user.username,
        roles: auth.user.roles,
      }
    },
  })

  if (typeof window !== 'undefined' && window.parent !== window) {
    window.parent.postMessage({ type: 'desktop-web-ready' }, '*')
  }
}
