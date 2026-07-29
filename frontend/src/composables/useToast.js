import { ref, inject } from 'vue'

export function useToast() {
  const toast = inject('$toast')
  if (!toast) {
    // fallback for cases where toast is not injected
    const fallback = {
      success: (msg) => console.log('[success]', msg),
      error: (msg) => console.error('[error]', msg),
      info: (msg) => console.log('[info]', msg),
      warning: (msg) => console.warn('[warning]', msg),
    }
    return fallback
  }
  return toast
}

