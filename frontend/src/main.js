import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import Toast from './components/Toast.vue'
import { toastRef } from './composables/useToastRef'

const app = createApp(App)
app.use(router)

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
