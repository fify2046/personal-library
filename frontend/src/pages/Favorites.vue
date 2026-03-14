<template>
  <div class="favorites-page">
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
        <div class="menu-item active">
          <el-icon><Star /></el-icon>
          <span>我的收藏</span>
        </div>
        <div class="menu-item" @click="$router.push('/reading')">
          <el-icon><Reading /></el-icon>
          <span>阅读列表</span>
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
          <h1>我的收藏</h1>
        </div>
      </header>
      
      <div class="content-area" v-loading="loading">
        <div v-if="favorites.length === 0 && !loading" class="empty-state">
          <el-icon class="empty-icon"><Star /></el-icon>
          <p>暂无收藏图书</p>
          <el-button type="primary" @click="$router.push('/')">去添加收藏</el-button>
        </div>
        
        <div v-else class="book-grid">
          <div 
            v-for="book in favorites" 
            :key="book.book_id" 
            class="book-card"
            @click="goToDetail(book.book_id)"
          >
            <div class="book-cover">
              <div class="cover-placeholder">
                <el-icon><Document /></el-icon>
              </div>
              <span class="file-type-badge">{{ book.file_type.toUpperCase() }}</span>
            </div>
            <div class="book-info">
              <h3 class="book-title">{{ book.title }}</h3>
              <p class="book-author">{{ book.author || '未知作者' }}</p>
              <p class="add-time">收藏于: {{ formatDate(book.add_time) }}</p>
            </div>
            <el-button 
              class="delete-btn" 
              type="danger" 
              :icon="Delete" 
              circle
              @click.stop="removeFavorite(book.book_id)"
            />
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Back, Fold, Expand, Star, Reading, Document, Delete, HomeFilled, Setting } from '@element-plus/icons-vue'
import api from '@/utils/api.js'

const router = useRouter()
const sidebarCollapsed = ref(false)
const loading = ref(false)
const favorites = ref([])

const loadFavorites = async () => {
  loading.value = true
  try {
    const res = await api.getFavorites()
    favorites.value = res.data || []
  } catch (error) {
    ElMessage.error('加载收藏列表失败')
  } finally {
    loading.value = false
  }
}

const removeFavorite = async (bookId) => {
  try {
    await ElMessageBox.confirm('确定要取消收藏吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await api.removeFavorite(bookId)
    ElMessage.success('取消收藏成功')
    loadFavorites()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('取消收藏失败')
    }
  }
}

const goToDetail = (bookId) => {
  sessionStorage.setItem('returnPath', '/favorites')
  router.push(`/book/${bookId}`)
}

const formatDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadFavorites()
})
</script>

<style scoped>
.favorites-page {
  display: flex;
  min-height: 100vh;
  background: var(--bg-primary);
}

.sidebar {
  width: 240px;
  background: var(--card-bg);
  border-right: 1px solid var(--border-color);
  transition: width 0.3s;
  flex-shrink: 0;
}

.sidebar.collapsed {
  width: 60px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
}

.sidebar-header h3 {
  margin: 0;
  font-size: 18px;
}

.menu-list {
  padding: 16px 0;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  cursor: pointer;
  transition: background 0.2s;
}

.menu-item:hover {
  background: var(--hover-bg);
}

.menu-item.active {
  background: var(--bg-secondary);
  color: var(--el-color-primary);
}

.menu-item .el-icon {
  font-size: 20px;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: var(--card-bg);
  border-bottom: 1px solid var(--border-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h1 {
  margin: 0;
  font-size: 20px;
}

.content-area {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 20px;
}

.book-card {
  background: var(--card-bg);
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  position: relative;
}

.book-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.book-cover {
  position: relative;
  height: 180px;
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.cover-placeholder {
  font-size: 48px;
  color: var(--text-secondary);
}

.file-type-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: var(--el-color-primary);
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.book-info {
  padding: 12px;
}

.book-title {
  margin: 0 0 8px 0;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.book-author {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.add-time {
  margin: 8px 0 0 0;
  font-size: 11px;
  color: var(--text-secondary);
}

.delete-btn {
  position: absolute;
  top: 8px;
  left: 8px;
  opacity: 0;
  transition: opacity 0.2s;
}

.book-card:hover .delete-btn {
  opacity: 1;
}
</style>
