import { ref } from 'vue'

// 独立的 toastRef，避免 main.js ↔ App.vue 循环依赖
export const toastRef = ref(null)
