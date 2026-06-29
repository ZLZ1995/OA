/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ROUTER_BASE?: string
  readonly VITE_API_BASE_URL?: string
}

interface DesktopWebStatePayload {
  currentRoute: string
  workspaceKey: 'admin' | 'business' | ''
  userId: number | null
}

interface DesktopBridgeSessionUser {
  userId: number
  username: string
  displayName: string
  roles: string[]
}

interface DesktopBridgeSessionPayload {
  accountId: string
  accessToken: string
  user: DesktopBridgeSessionUser
}

interface DesktopBridgeRoutePayload {
  path: string
}

interface DesktopBridgeWorkspacePayload {
  workspaceKey: 'admin' | 'business'
}

interface Window {
  desktopApp?: {
    version: string
    isDesktopShell?: boolean
    getRuntimeConfig?: () => Promise<{
      backendUrl: string
    }>
    getSettingsState: () => Promise<unknown>
    getSessionState?: () => Promise<{
      phase: 'login_form' | 'workspace_select' | 'oa_active' | 'fallback_web_login'
      accounts: Array<{
        accountId: string
        userId: number
        username: string
        displayName: string
        roles: string[]
        accessToken: string
        workspaceKey: 'admin' | 'business' | ''
        lastRoute: string
      }>
      activeAccountId: string
      activeAccount: {
        accountId: string
        userId: number
        username: string
        displayName: string
        roles: string[]
        accessToken: string
        workspaceKey: 'admin' | 'business' | ''
        lastRoute: string
      } | null
      currentRoute: string
      workspaceKey: 'admin' | 'business' | ''
      currentUserId: number | null
      workspaceOptions: Array<'admin' | 'business'>
    }>
    login?: (payload: { username: string; password: string }) => Promise<unknown>
    logout?: () => Promise<unknown>
    requestAccountSwitch?: () => Promise<unknown>
    applySession?: (payload: DesktopBridgeSessionPayload) => Promise<unknown>
    activateAccount?: (accountId: string) => Promise<unknown>
    setWorkspace?: (workspaceKey: 'admin' | 'business') => Promise<unknown>
    navigateRoute?: (path: string) => Promise<unknown>
    savePreferences: (payload: {
      autoStartEnabled: boolean
      rememberCloseChoice: boolean
      closeBehavior: 'ask' | 'exit' | 'tray'
      downloadDefaultDir: string
    }) => Promise<unknown>
    chooseDownloadDirectory: () => Promise<string>
    saveServiceEndpoints: (payload: { backendUrl: string }) => Promise<unknown>
    resetServiceEndpoints: () => Promise<unknown>
    handleNotificationAction: (actionKey: string) => void
    notifyWebState?: (payload: DesktopWebStatePayload) => Promise<void>
  }
  desktopBridge?: {
    applySession: (payload: DesktopBridgeSessionPayload) => Promise<void> | void
    clearSession: () => Promise<void> | void
    navigateTo: (payload: DesktopBridgeRoutePayload) => Promise<void> | void
    setWorkspace: (payload: DesktopBridgeWorkspacePayload) => Promise<void> | void
    getCurrentRoute: () => string
    getCurrentUser: () => DesktopBridgeSessionUser | null
  }
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
}
