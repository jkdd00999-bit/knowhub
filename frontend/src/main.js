import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import Toast from './components/Toast.vue'
import { setToastRef } from './composables/useRequest'

const app = createApp(App)
app.use(router)

// Toast plugin
app.component('Toast', Toast)
const toastApi = {
  success: (msg, duration) => app._toastInstance?.add('success', msg, duration),
  error: (msg, duration) => app._toastInstance?.add('error', msg, duration),
  info: (msg, duration) => app._toastInstance?.add('info', msg, duration),
  warning: (msg, duration) => app._toastInstance?.add('warning', msg, duration),
}
app.provide('$toast', toastApi)
app.config.globalProperties.$toast = toastApi

app.mount('#app')

// Deferred toast binding: App.vue exposes toastRef via provide, but
// the Toast component mounts after App, so we bridge via a watcher-free approach.
// The App.vue onMounted will call setToastRef.
export { setToastRef }
