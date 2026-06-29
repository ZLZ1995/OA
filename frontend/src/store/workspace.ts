import { defineStore } from 'pinia'
import { isDesktopShell, notifyDesktopStateChanged } from '@/utils/desktop'

export type WorkspaceMode = 'admin' | 'business'

const WORKSPACE_STORAGE_KEY = 'workspace_mode'

function readWorkspaceFromSession(): WorkspaceMode | null {
  const value = sessionStorage.getItem(WORKSPACE_STORAGE_KEY)
  if (value === 'admin' || value === 'business') {
    return value
  }

  const desktopValue = localStorage.getItem('desktop_workspace_mode')
  return desktopValue === 'admin' || desktopValue === 'business' ? desktopValue : null
}

function hasAdminRole(roles: string[]) {
  return roles.includes('ADMIN')
}

function hasNonAdminRole(roles: string[]) {
  return roles.some(role => role !== 'ADMIN')
}

export const useWorkspaceStore = defineStore('workspace', {
  state: () => ({
    currentWorkspace: readWorkspaceFromSession() as WorkspaceMode | null,
  }),
  getters: {
    isAdminWorkspace: (state) => state.currentWorkspace === 'admin',
    isBusinessWorkspace: (state) => state.currentWorkspace === 'business',
  },
  actions: {
    clearWorkspace() {
      this.currentWorkspace = null
      sessionStorage.removeItem(WORKSPACE_STORAGE_KEY)
      localStorage.removeItem('desktop_workspace_mode')
      void notifyDesktopStateChanged({
        currentRoute: window.location.pathname + window.location.search,
        workspaceKey: '',
        userId: null,
      })
    },
    setWorkspace(workspace: WorkspaceMode) {
      this.currentWorkspace = workspace
      sessionStorage.setItem(WORKSPACE_STORAGE_KEY, workspace)
      if (localStorage.getItem('desktop_shell_mode') === 'true') {
        localStorage.setItem('desktop_workspace_mode', workspace)
      }
      void notifyDesktopStateChanged({
        currentRoute: window.location.pathname + window.location.search,
        workspaceKey: workspace,
        userId: null,
      })
    },
    supportsWorkspaceChoice(roles: string[]) {
      return hasAdminRole(roles) && hasNonAdminRole(roles)
    },
    resolveDefaultWorkspace(roles: string[]): WorkspaceMode | null {
      if (hasAdminRole(roles) && !hasNonAdminRole(roles)) {
        return 'admin'
      }
      if (!hasAdminRole(roles) && hasNonAdminRole(roles)) {
        return 'business'
      }
      return null
    },
    initializeForRoles(roles: string[]) {
      const defaultWorkspace = this.resolveDefaultWorkspace(roles)
      if (defaultWorkspace) {
        this.setWorkspace(defaultWorkspace)
        return defaultWorkspace
      }
      if (this.supportsWorkspaceChoice(roles)) {
        const current = readWorkspaceFromSession()
        if (current) {
          this.currentWorkspace = current
          return current
        }

        if (isDesktopShell()) {
          this.setWorkspace('business')
          return 'business'
        }

        this.currentWorkspace = null
        return current
      }
      this.clearWorkspace()
      return null
    },
    canAccessWorkspace(roles: string[], workspace: WorkspaceMode) {
      if (workspace === 'admin') {
        return hasAdminRole(roles)
      }
      return hasNonAdminRole(roles)
    },
  },
})
