import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'

import App from './App.vue'
import router from './router'
import { pinia } from './store/pinia'
import { installDesktopBridge, isDesktopEmbedded, syncDesktopModeAttribute } from './utils/desktop'
import './styles/index.scss'

async function bootstrap() {
  syncDesktopModeAttribute()

  if (isDesktopEmbedded()) {
    try {
      const runtimeConfig = await window.desktopApp?.getRuntimeConfig?.()
      if (runtimeConfig?.backendUrl) {
        localStorage.setItem('desktop_backend_url', runtimeConfig.backendUrl.replace(/\/+$/, ''))
      }
    } catch {
      localStorage.removeItem('desktop_backend_url')
    }
  } else {
    localStorage.removeItem('desktop_backend_url')
  }

  installDesktopBridge(router)

  const app = createApp(App)
  app.use(pinia)
  app.use(router)
  app.use(ElementPlus)
  app.mount('#app')
}

void bootstrap()
