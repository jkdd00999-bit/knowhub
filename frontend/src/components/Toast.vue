<template>
  <Teleport to="body">
    <TransitionGroup name="toast" tag="div" class="toast-container">
      <div
        v-for="t in toasts"
        :key="t.id"
        :class="['toast', 'toast--' + t.type]"
      >
        <span class="toast__icon">{{ iconMap[t.type] }}</span>
        <span class="toast__msg">{{ t.message }}</span>
        <button class="toast__close" @click="dismiss(t.id)">&times;</button>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'

const toasts = ref([])
let seq = 0

const iconMap = { success: '\u2714', error: '\u2716', info: '\u2139', warning: '\u26A0' }

function add(type, message, duration = 4000) {
  const id = ++seq
  toasts.value.push({ id, type, message })
  if (duration > 0) {
    setTimeout(() => dismiss(id), duration)
  }
}

function dismiss(id) {
  const idx = toasts.value.findIndex(t => t.id === id)
  if (idx > -1) toasts.value.splice(idx, 1)
}

defineExpose({ add, dismiss })
</script>

<style>
.toast-container {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 10000;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 380px;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 10px;
  font-size: 14px;
  line-height: 1.5;
  box-shadow: 0 4px 20px rgba(0,0,0,.12);
  color: #fff;
  word-break: break-word;
}
.toast--success { background: #059669; }
.toast--error   { background: #dc2626; }
.toast--info    { background: var(--primary); }
.toast--warning { background: #d97706; }

.toast__icon { flex-shrink: 0; font-size: 16px; line-height: 1.5; }
.toast__msg  { flex: 1; }
.toast__close {
  flex-shrink: 0;
  background: none;
  border: none;
  color: rgba(255,255,255,.8);
  font-size: 18px;
  cursor: pointer;
  line-height: 1;
  padding: 0 2px;
}
.toast__close:hover { color: #fff; }

.toast-enter-active { transition: all .3s ease; }
.toast-leave-active { transition: all .25s ease; }
.toast-enter-from    { opacity: 0; transform: translateX(40px); }
.toast-leave-to      { opacity: 0; transform: translateX(40px); }
</style>
