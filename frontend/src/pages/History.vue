<template>
  <div class="history-page">
    <aside class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <h3>{{ sidebarCollapsed ? '' : '菜单' }}</h3>
        <el-button 
          :icon="sidebarCollapsed ? Expand : Fold" 
          text 
          @click="sidebarCollapsed = !sidebarCollapsed"
          class="collapse-btn"
        />
      </div>
      
      <div class="menu-list" v-if="!sidebarCollapsed">
        <div class="menu-item" @click="$router.push('/')">
          <el-icon><HomeFilled /></el-icon>
          <span>图书列表</span>
        </div>
        <div class="menu-item" @click="$router.push('/reading')">
          <el-icon><Reading /></el-icon>
          <span>我的阅读</span>
        </div>
        <div class="menu-item active">
          <el-icon><Clock /></el-icon>
          <span>阅读历史</span>
        </div>
        <div class="menu-item" @click="$router.push('/manage')">
          <el-icon><Setting /></el-icon>
          <span>图书管理</span>
        </div>
      </div>
    </aside>
    
    <main class="main-content">
      <header class="page-header">
        <div class="header-left">
          <el-button :icon="Back" circle @click="$router.push('/')" />
          <h1>阅读历史</h1>
        </div>
        <div class="header-right">
          <el-button 
            type="danger" 
            :disabled="historyList.length === 0"
            @click="clearAllHistory"
          >
            一键清除
          </el-button>
        </div>
      </header>
      
      <div class="content-area" v-loading="loading">
        <el-table 
          :data="historyList" 
          style="width: 100%"
        >
          <el-table-column prop="book_title" label="书名" min-width="200">
            <template #default="scope">
              <a class="book-link" @click="goToDetail(scope.row.book_id)">{{ scope.row.book_title }}</a>
            </template>
          </el-table-column>
          <el-table-column prop="author" label="作者" width="150" />
          <el-table-column label="阅读进度" width="120">
            <template #default="scope">
              <el-progress 
                :percentage="scope.row.progress" 
                :stroke-width="10"
                :show-text="false"
              />
              <span class="progress-text">{{ scope.row.progress }}%</span>
            </template>
          </el-table-column>
          <el-table-column label="阅读时长" width="120">
            <template #default="scope">
              {{ formatDuration(scope.row.read_duration) }}
            </template>
          </el-table-column>
          <el-table-column label="最后阅读时间" width="180">
            <template #default="scope">
              {{ formatDateTime(scope.row.read_time) }}
            </template>
          </el-table-column>
        </el-table>
        
        <div class="pagination-wrapper">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="total"
            :page-sizes="[20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @size-change="fetchHistory"
            @current-change="fetchHistory"
          />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Back, Reading, Clock, Setting, HomeFilled, Expand, Fold } from '@element-plus/icons-vue'
import api from '@/utils/api.js'

const router = useRouter()

const historyList = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const sidebarCollapsed = ref(false)

const fetchHistory = async () => {
  loading.value = true
  try {
    const res = await api.getReadingHistory({
      page: currentPage.value,
      size: pageSize.value
    })
    historyList.value = res.data?.list || res.list || []
    total.value = res.data?.total || res.total || 0
  } catch (error) {
    console.error('Failed to fetch history:', error)
  } finally {
    loading.value = false
  }
}

const goToDetail = (bookId) => {
  sessionStorage.setItem('returnPath', '/history')
  sessionStorage.setItem('history_page_state', JSON.stringify({
    currentPage: currentPage.value,
    pageSize: pageSize.value
  }))
  router.push(`/book/${bookId}`)
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatDuration = (seconds) => {
  if (!seconds) return '0分钟'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  }
  return `${minutes}分钟`
}

const clearAllHistory = async () => {
  try {
    await ElMessageBox.confirm('确定要清空所有阅读历史吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
      distinguishCancelAndClose: true,
      defaultFocus: 'cancel'
    })
    
    await api.clearReadingHistory()
    ElMessage.success('阅读历史已清空')
    fetchHistory()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('清空失败')
    }
  }
}

onMounted(() => {
  const savedState = sessionStorage.getItem('history_page_state')
  if (savedState) {
    const state = JSON.parse(savedState)
    currentPage.value = state.currentPage || 1
    pageSize.value = state.pageSize || 20
    sessionStorage.removeItem('history_page_state')
  }
  fetchHistory()
})
</script>

<style scoped>
.history-page {
  display: flex;
  min-height: 100vh;
  background: var(--bg-color);
}

.sidebar {
  width: 240px;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border-color);
  transition: width 0.3s;
  position: fixed;
  height: 100vh;
  z-index: 10;
}

.sidebar.collapsed {
  width: 60px;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--text-primary);
}

.collapse-btn {
  padding: 4px;
}

.menu-list {
  padding: 8px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.menu-item:hover {
  background: var(--hover-bg);
}

.menu-item.active {
  background: var(--hover-bg);
  color: var(--primary-color);
}

.menu-item .el-icon {
  font-size: 20px;
}

.main-content {
  flex: 1;
  margin-left: 240px;
  padding: 24px 32px;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h1 {
  margin: 0;
  font-size: 24px;
  color: var(--text-primary);
}

.content-area {
  background: var(--card-bg);
  border-radius: 8px;
  padding: 24px;
}

.pagination-wrapper {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}

.progress-text {
  font-size: 12px;
  color: var(--text-secondary);
  margin-left: 8px;
}

.book-link {
  color: var(--primary-color);
  cursor: pointer;
  text-decoration: none;
}

.book-link:hover {
  text-decoration: underline;
}

:deep(.el-table) {
  --el-table-border-color: var(--border-color);
  --el-table-header-bg-color: var(--hover-bg);
}

:deep(.el-table th) {
  background: var(--hover-bg) !important;
}
</style>
