import { createApp, ref } from 'vue'
import App from './App.vue'
import router from './router'
import Toast from './components/Toast.vue'

const app = createApp(App)
app.use(router)

// Toast: use a shared ref so toastApi works before App.vue mounts
export const toastRef = ref(null)

app.component('Toast', Toast)
const toastApi = {
  success: (msg, duration) => toastRef.value?.add('success', msg, duration),
  error: (msg, duration) => toastRef.value?.add('error', msg, duration),
  info: (msg, duration) => toastRef.value?.add('info', msg, duration),
  warning: (msg, duration) => toastRef.value?.add('warning', msg, duration),
}
app.provide('$toast', toastApi)
app.config.globalProperties.$toast = toastApi

app.mount('#app')
