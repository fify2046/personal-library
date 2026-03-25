<template>
  <div class="manage-page">
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
        <div class="menu-item" @click="$router.push('/history')">
          <el-icon><Clock /></el-icon>
          <span>阅读历史</span>
        </div>
        <div class="menu-item active">
          <el-icon><Setting /></el-icon>
          <span>图书管理</span>
        </div>
        <div class="menu-item" @click="$router.push('/system-config')">
          <el-icon><Tools /></el-icon>
          <span>系统管理</span>
        </div>
      </div>
    </aside>
    
    <main class="main-content">
      <header class="page-header">
        <div class="header-left">
          <el-button :icon="Back" circle @click="$router.push('/')" />
          <h1>图书管理</h1>
        </div>
      </header>
      
      <div class="search-bar">
        <el-input
          v-model="keyword"
          placeholder="搜索书名或作者..."
          clearable
          @input="handleSearch"
          class="search-input"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        
        <el-radio-group v-model="fileType" @change="fetchBooks">
          <el-radio-button value="">全部</el-radio-button>
          <el-radio-button value="pdf">PDF</el-radio-button>
          <el-radio-button value="epub">EPUB</el-radio-button>
        </el-radio-group>
        
        <div class="header-actions">
          <el-button @click="toggleSelectAll">
            {{ isAllSelected ? '取消全选' : '全选' }}
          </el-button>
          <el-button 
            type="danger" 
            :disabled="selectedBooks.length === 0"
            @click="deleteSelected"
          >
            删除选中项 ({{ selectedBooks.length }})
          </el-button>
        </div>
      </div>
      
      <div class="content-area" v-loading="loading">
        <el-table 
          :data="books" 
          style="width: 100%"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="title" label="书名" min-width="200">
            <template #default="scope">
              <a class="book-link" @click="goToDetail(scope.row.book_id)">{{ scope.row.title }}</a>
            </template>
          </el-table-column>
          <el-table-column prop="author" label="作者" width="150" />
          <el-table-column prop="publisher" label="出版社" width="150" />
          <el-table-column prop="publish_date" label="出版日期" width="120" />
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="scope">
              <el-button size="small" @click="handleEdit(scope.row)">
                修改
              </el-button>
              <el-button 
                size="small" 
                type="danger" 
                @click="handleDelete(scope.row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        
        <div class="pagination-wrapper">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @size-change="fetchBooks"
            @current-change="fetchBooks"
          />
        </div>
      </div>
    </main>
    
    <el-dialog v-model="editDialogVisible" title="修改图书信息" width="500px">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="书名">
          <el-input v-model="editForm.title" />
        </el-form-item>
        <el-form-item label="作者">
          <el-input v-model="editForm.author" />
        </el-form-item>
        <el-form-item label="出版社">
          <el-input v-model="editForm.publisher" />
        </el-form-item>
        <el-form-item label="出版日期">
          <el-input v-model="editForm.publish_date" />
        </el-form-item>
        <el-form-item label="ISBN">
          <el-input v-model="editForm.isbn" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Back, Star, Reading, Setting, HomeFilled, Expand, Fold, Clock, Tools } from '@element-plus/icons-vue'
import api from '@/utils/api.js'

const router = useRouter()

const books = ref([])
const loading = ref(false)
const keyword = ref('')
const fileType = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const selectedBooks = ref([])
const sidebarCollapsed = ref(false)

const editDialogVisible = ref(false)
const editForm = ref({
  book_id: '',
  title: '',
  author: '',
  publisher: '',
  publish_date: '',
  isbn: ''
})

const isAllSelected = computed(() => {
  return books.value.length > 0 && selectedBooks.value.length === books.value.length
})

const fetchBooks = async () => {
  loading.value = true
  try {
    const res = await api.getBooks({
      page: currentPage.value,
      size: pageSize.value,
      keyword: keyword.value,
      type: fileType.value,
      all_books: true
    })
    books.value = res.list || []
    total.value = res.total || 0
  } catch (error) {
    console.error('Failed to fetch books:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
  fetchBooks()
}

const handleSelectionChange = (selection) => {
  selectedBooks.value = selection
}

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedBooks.value = []
  } else {
    selectedBooks.value = [...books.value]
  }
}

const handleEdit = (row) => {
  editForm.value = {
    book_id: row.book_id,
    title: row.title || '',
    author: row.author || '',
    publisher: row.publisher || '',
    publish_date: row.publish_date || '',
    isbn: row.isbn || ''
  }
  editDialogVisible.value = true
}

const saveEdit = async () => {
  try {
    await api.updateBook(editForm.value.book_id, {
      title: editForm.value.title,
      author: editForm.value.author,
      publisher: editForm.value.publisher,
      publish_date: editForm.value.publish_date,
      isbn: editForm.value.isbn
    })
    ElMessage.success('修改成功')
    editDialogVisible.value = false
    fetchBooks()
  } catch (error) {
    ElMessage.error('修改失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该图书吗？删除后无法恢复！', '警告', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
      distinguishCancelAndClose: true,
      defaultFocus: 'cancel'
    })
    
    await api.deleteBook(row.book_id)
    ElMessage.success('删除成功')
    fetchBooks()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const deleteSelected = async () => {
  if (selectedBooks.value.length === 0) return
  
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedBooks.value.length} 本图书吗？删除后无法恢复！`, '警告', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning',
      distinguishCancelAndClose: true,
      defaultFocus: 'cancel'
    })
    
    for (const book of selectedBooks.value) {
      await api.deleteBook(book.book_id)
    }
    ElMessage.success('批量删除成功')
    selectedBooks.value = []
    fetchBooks()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const goToDetail = (bookId) => {
  sessionStorage.setItem('returnPath', '/manage')
  sessionStorage.setItem('manage_page_state', JSON.stringify({
    keyword: keyword.value,
    fileType: fileType.value,
    currentPage: currentPage.value,
    pageSize: pageSize.value
  }))
  router.push(`/book/${bookId}`)
}

onMounted(() => {
  const savedState = sessionStorage.getItem('manage_page_state')
  if (savedState) {
    const state = JSON.parse(savedState)
    keyword.value = state.keyword || ''
    fileType.value = state.fileType || ''
    currentPage.value = state.currentPage || 1
    pageSize.value = state.pageSize || 20
    sessionStorage.removeItem('manage_page_state')
  }
  fetchBooks()
})
</script>

<style scoped>
.manage-page {
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
  transition: margin-left 0.3s;
}

.sidebar.collapsed + .main-content {
  margin-left: 60px;
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

.search-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.search-input {
  width: 300px;
}

.header-actions {
  margin-left: auto;
  display: flex;
  gap: 12px;
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

:deep(.el-table) {
  --el-table-border-color: var(--border-color);
  --el-table-header-bg-color: var(--hover-bg);
}

:deep(.el-table th) {
  background: var(--hover-bg) !important;
}

:deep(.el-dialog) {
  background: var(--card-bg);
}

.book-link {
  color: var(--primary-color);
  cursor: pointer;
  text-decoration: none;
}

.book-link:hover {
  text-decoration: underline;
}
</style>
