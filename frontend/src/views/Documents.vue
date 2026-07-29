<template>
  <div class="documents-page">
    <div class="page-header">
      <h1>📄 文档管理</h1>
      <p>上传、管理你的企业知识库文档</p>
    </div>

    <!-- 上传区域 -->
    <div class="upload-section">
      <div
        class="upload-area"
        :class="{ 'drag-over': isDragging }"
        @dragover.prevent="isDragging = true"
        @dragleave="isDragging = false"
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <div class="upload-icon">📤</div>
        <h3>点击或拖拽文件到此处上传</h3>
        <p>支持 PDF、Word、Markdown、TXT 格式，单个文件最大 50MB</p>
        <input
          type="file"
          ref="fileInput"
          @change="handleFileSelect"
          multiple
          accept=".pdf,.txt,.docx,.md"
          style="display: none"
        />
      </div>

      <!-- 上传进度 -->
      <div v-if="uploading" class="upload-progress">
        <div class="progress-header">
          <span>正在上传 {{ currentFile }}</span>
          <span>{{ uploadProgress }}%</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
        </div>
      </div>
    </div>

    <!-- 文档列表 -->
    <div class="documents-section">
      <div class="section-header">
        <h2>已上传文档 ({{ documents.length }})</h2>
        <button @click="loadDocuments" class="refresh-btn">🔄 刷新</button>
      </div>

      <div v-if="loading" class="loading-state">
        <div v-for="n in 5" :key="n" class="skeleton-item">
          <SkeletonLoader width="60%" height="16px" />
          <SkeletonLoader width="30%" height="12px" style="margin-top:8px" />
        </div>
      </div>

      <div v-else-if="documents.length === 0" class="empty-state">
        <div class="empty-icon">📄</div>
        <p>还没有上传文档</p>
        <p class="empty-hint">上传文档后，系统会自动解析、切分、向量化</p>
      </div>

      <div v-else class="documents-list">
        <div v-for="doc in documents" :key="doc.id" class="document-item">
          <div class="doc-icon">{{ getFileIcon(doc.file_type) }}</div>
          <div class="doc-info">
            <div class="doc-title">{{ doc.title }}</div>
            <div class="doc-meta">
              <span class="category-tag">{{ doc.category }}</span>
              <span>{{ doc.summary }}</span>
            </div>
          </div>
          <div class="doc-actions">
            <button @click="viewDocument(doc)" class="action-btn">查看</button>
            <button @click="deleteDocument(doc.id)" class="action-btn delete">删除</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SkeletonLoader from '../components/SkeletonLoader.vue'
import { useToast } from '../composables/useToast'

const toast = useToast()

const router = useRouter()
const fileInput = ref(null)
const isDragging = ref(false)
const uploading = ref(false)
const currentFile = ref('')
const uploadProgress = ref(0)
const loading = ref(true)
const documents = ref([])

function getFileIcon(fileType) {
  const icons = {
    'pdf': '📕',
    'txt': '📄',
    'docx': '📘',
    'md': '📝'
  }
  return icons[fileType] || '📄'
}

function triggerFileInput() {
  fileInput.value?.click()
}

function handleFileSelect(event) {
  const files = event.target.files
  if (files.length > 0) {
    uploadFiles(Array.from(files))
  }
}

function handleDrop(event) {
  isDragging.value = false
  const files = event.dataTransfer.files
  if (files.length > 0) {
    uploadFiles(Array.from(files))
  }
}

async function uploadFiles(files) {
  const token = localStorage.getItem('token')
  if (!token) {
    toast.warning('请先登录')
    router.push('/login')
    return
  }

  uploading.value = true

  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    currentFile.value = file.name
    uploadProgress.value = 0

    try {
      const formData = new FormData()
      formData.append('file', file)

      // 模拟进度更新
      const progressInterval = setInterval(() => {
        if (uploadProgress.value < 90) {
          uploadProgress.value += 10
        }
      }, 200)

      const response = await fetch('/api/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })

      clearInterval(progressInterval)
      uploadProgress.value = 100

      if (!response.ok) {
        throw new Error(`上传失败: ${response.statusText}`)
      }

      const result = await response.json()
      console.log('上传成功:', result)

    } catch (error) {
      console.error('上传错误:', error)
      toast.error(`上传 ${file.name} 失败`)
    }
  }

  uploading.value = false
  currentFile.value = ''
  uploadProgress.value = 0

  // 刷新文档列表
  await loadDocuments()

  // 清空文件输入
  if (fileInput.value) {
    fileInput.value.value = ''
  }

  toast.success(`成功上传 ${files.length} 个文件！`)
}

async function loadDocuments() {
  loading.value = true
  try {
    const token = localStorage.getItem('token')
    if (!token) {
      documents.value = []
      return
    }

    const response = await fetch('/api/docs', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (response.ok) {
      const result = await response.json()
      documents.value = result
    }
  } catch (error) {
    console.error('加载文档失败:', error)
  } finally {
    loading.value = false
  }
}

async function viewDocument(doc) {
  router.push(`/docs/${doc.id}`)
}

async function deleteDocument(docId) {
  if (!confirm('确定要删除这个文档吗？')) {
    return
  }

  try {
    const token = localStorage.getItem('token')
    const response = await fetch(`/api/docs/${docId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    if (response.ok) {
      await loadDocuments()
      toast.success('删除成功')
    } else {
      throw new Error('删除失败')
    }
  } catch (error) {
    console.error('删除错误:', error)
    toast.error('删除失败')
  }
}

onMounted(() => {
  loadDocuments()
})
</script>

<style scoped>
.documents-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  margin-bottom: 32px;
}

.page-header h1 {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
}

.page-header p {
  color: var(--text-muted);
  font-size: 14px;
}

.upload-section {
  margin-bottom: 40px;
}

.upload-area {
  border: 2px dashed var(--border);
  border-radius: 12px;
  padding: 48px 24px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: var(--bg);
}

.upload-area:hover,
.upload-area.drag-over {
  border-color: var(--primary);
  background: #f1f5f9;
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.upload-area h3 {
  font-size: 18px;
  margin-bottom: 8px;
}

.upload-area p {
  color: var(--text-muted);
  font-size: 14px;
}

.upload-progress {
  margin-top: 20px;
  padding: 16px;
  background: var(--bg);
  border-radius: 8px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 14px;
}

.progress-bar {
  height: 8px;
  background: var(--border);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--primary);
  transition: width 0.3s ease;
}

.documents-section {
  margin-top: 40px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h2 {
  font-size: 20px;
  font-weight: 600;
}

.refresh-btn {
  padding: 8px 16px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s ease;
}

.refresh-btn:hover {
  background: #f1f5f9;
  border-color: var(--primary);
}

.loading-state {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-item {
  background: var(--bg);
  border-radius: 8px;
  padding: 16px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: var(--bg);
  border-radius: 12px;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-state p {
  font-size: 16px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 14px;
  color: var(--text-muted);
}

.documents-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.document-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: var(--bg);
  border-radius: 8px;
  transition: all 0.2s ease;
}

.document-item:hover {
  background: #f1f5f9;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.doc-icon {
  font-size: 32px;
  flex-shrink: 0;
}

.doc-info {
  flex: 1;
  min-width: 0;
}

.doc-title {
  font-size: 15px;
  font-weight: 500;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-meta {
  display: flex;
  gap: 12px;
  font-size: 13px;
  color: var(--text-muted);
}

.category-tag {
  padding: 2px 8px;
  background: var(--primary-light);
  color: white;
  border-radius: 4px;
  font-size: 12px;
}

.doc-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.action-btn {
  padding: 6px 12px;
  background: white;
  border: 1px solid var(--border);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s ease;
}

.action-btn:hover {
  background: #f1f5f9;
  border-color: var(--primary);
  color: var(--primary);
}

.action-btn.delete:hover {
  background: #fee;
  border-color: #f44;
  color: #f44;
}

@media (max-width: 768px) {
  .document-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .doc-actions {
    width: 100%;
    margin-top: 12px;
  }

  .action-btn {
    flex: 1;
  }
}
</style>
