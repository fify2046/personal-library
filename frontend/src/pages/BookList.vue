<template>
  <div class="book-list-page">
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1 class="logo">📚 个人图书馆</h1>
      </div>
      
      <div class="search-box">
        <el-input
          v-model="keyword"
          placeholder="搜索书名/作者/内容..."
          clearable
          @keyup.enter="handleSearch"
          @input="handleKeywordChange"
          @clear="handleKeywordClear"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
      
      <div class="search-options">
        <el-checkbox v-model="fullTextSearch" @change="handleSearchTypeChange">全文搜索</el-checkbox>
      </div>
      
      <div class="filter-tags">
        <el-tag 
          :type="fileType === '' ? 'primary' : 'info'" 
          @click="handleTypeChange('')"
          class="filter-tag"
        >
          全部
        </el-tag>
        <el-tag 
          :type="fileType === 'pdf' ? 'primary' : 'info'" 
          @click="handleTypeChange('pdf')"
          class="filter-tag"
        >
          PDF
        </el-tag>
        <el-tag 
          :type="fileType === 'epub' ? 'primary' : 'info'" 
          @click="handleTypeChange('epub')"
          class="filter-tag"
        >
          EPUB
        </el-tag>
      </div>
      
      <div class="reading-history" v-if="readingHistory.length > 0">
        <div class="history-header">
          <span class="history-title">阅读历史</span>
          <el-button 
            type="danger" 
            size="small" 
            text 
            @click="clearHistory"
          >
            清除
          </el-button>
        </div>
        <div class="history-list">
          <div 
            v-for="item in readingHistory" 
            :key="item.id"
            class="history-item"
            @click="goToReading(item)"
          >
            <div class="history-book-title">{{ item.book_title }}</div>
            <div class="history-chapter">{{ item.chapter_name }}</div>
          </div>
        </div>
      </div>
      
      <div class="sidebar-footer">
        <el-switch
          v-model="isDarkMode"
          @change="handleDarkModeChange"
          active-text="深色模式"
          inactive-text="浅色模式"
        />
      </div>
    </aside>
    
    <main class="main-content">
      <div class="content-header">
        <div class="header-left">
          <el-radio-group v-model="sortBy" @change="handleSortChange">
            <el-radio-button value="recent">最近添加</el-radio-button>
            <el-radio-button value="title">书名排序</el-radio-button>
          </el-radio-group>
          
          <el-select v-model="columnsPerRow" placeholder="每行显示" style="width: 100px; margin-left: 12px;">
            <el-option :value="3" label="每行3本" />
            <el-option :value="4" label="每行4本" />
            <el-option :value="5" label="每行5本" />
            <el-option :value="6" label="每行6本" />
          </el-select>
          
          <el-button-group style="margin-left: 12px;">
            <el-button :type="viewMode === 'grid' ? 'primary' : 'default'" @click="viewMode = 'grid'">
              <el-icon><Grid /></el-icon>
            </el-button>
            <el-button :type="viewMode === 'list' ? 'primary' : 'default'" @click="viewMode = 'list'">
              <el-icon><List /></el-icon>
            </el-button>
          </el-button-group>
        </div>
        
        <div class="header-right">
          <el-button @click="backToNormalList" v-if="isSearchMode">
            <el-icon><Back /></el-icon>
            返回列表
          </el-button>
          <el-button @click="$router.push('/manage')">
            <el-icon><Setting /></el-icon>
            管理
          </el-button>
          <el-button @click="$router.push('/reading')">
            <el-icon><Reading /></el-icon>
            我的阅读
          </el-button>
          <el-button @click="$router.push('/history')">
            <el-icon><Clock /></el-icon>
            阅读历史
          </el-button>
          <span class="book-count" v-if="!isSearchMode">共 {{ total }} 本书</span>
          <span class="book-count" v-else>搜索到 {{ searchTotal }} 条结果</span>
        </div>
      </div>
      
      <div v-if="isSearchMode" class="search-results-container">
        <div 
          v-for="item in searchResults" 
          :key="item.matched_para_id ? item.matched_para_id : item.book_id + '_title'" 
          class="search-result-item"
          @click="goToSearchResult(item)"
        >
          <div class="result-cover">
            <el-image
              v-if="item.cover_path"
              :src="`/api/images/${encodeURIComponent(item.cover_path)}`"
              fit="cover"
              class="cover-image"
            >
              <template #error>
                <div class="cover-placeholder">
                  <el-icon><Document /></el-icon>
                </div>
              </template>
            </el-image>
            <div v-else class="cover-placeholder">
              <el-icon><Document /></el-icon>
            </div>
            <span class="file-type-badge">{{ item.file_type.toUpperCase() }}</span>
          </div>
          <div class="result-info">
            <h3 class="result-title">{{ item.title }}</h3>
            <p class="result-author">{{ item.author || '未知作者' }}</p>
            <p class="result-chapter" v-if="item.chapter_name">{{ item.chapter_name }}</p>
            <div class="result-snippet" v-if="item.matched_snippet">
              {{ item.matched_snippet }}
            </div>
          </div>
        </div>
        
        <div class="pagination-wrapper" v-if="searchTotal > searchPageSize">
          <el-pagination
            v-model:current-page="searchPage"
            :page-size="searchPageSize"
            :total="searchTotal"
            layout="total, prev, pager, next"
            @current-change="handleSearchPageChange"
          />
        </div>
      </div>
      
      <div 
        v-else
        class="book-container" 
        :class="[viewMode === 'grid' ? 'grid-view' : 'list-view', `cols-${columnsPerRow}`]"
        v-loading="loading"
      >
        <div 
          v-for="book in books" 
          :key="book.book_id" 
          class="book-card"
          @click="goToDetail(book.book_id)"
        >
          <div class="book-cover">
            <el-image
              v-if="book.cover_path"
              :src="`/api/images/${encodeURIComponent(book.cover_path)}`"
              fit="cover"
              class="cover-image"
            >
              <template #error>
                <div class="cover-placeholder">
                  <el-icon><Document /></el-icon>
                </div>
              </template>
            </el-image>
            <div v-else class="cover-placeholder">
              <el-icon><Document /></el-icon>
            </div>
            <span class="file-type-badge">{{ book.file_type.toUpperCase() }}</span>
          </div>
          <div class="book-info">
            <h3 class="book-title">{{ book.title }}</h3>
            <p class="book-author">{{ book.author || '未知作者' }}</p>
            <div class="book-meta">
              <span>{{ book.chapter_count }} 章</span>
              <span>{{ book.image_count }} 图</span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="pagination-wrapper" v-if="total > 0">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[12, 24, 48]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, inject, watch, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Search, Grid, List, Star, Reading, Document, Setting, Clock, Back } from '@element-plus/icons-vue'
import api from '@/utils/api.js'

const router = useRouter()
const route = useRoute()

const keyword = ref('')
const fileType = ref('')
const sortBy = ref('recent')
const currentPage = ref(1)
const pageSize = ref(12)
const total = ref(0)
const loading = ref(false)
const books = ref([])
const readingHistory = ref([])
const columnsPerRow = ref(4)
const viewMode = ref('grid')
const fullTextSearch = ref(false)
const searchResults = ref([])
const searchPage = ref(1)
const searchPageSize = ref(20)
const searchTotal = ref(0)
let searchTimeout = null

const isSearchMode = computed(() => searchResults.value.length > 0 || fullTextSearch.value)

const isDarkMode = inject('isDarkMode')
const setDarkMode = inject('setDarkMode')

const fetchBooks = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      size: pageSize.value,
      type: fileType.value || undefined,
      keyword: keyword.value || undefined,
      sort: sortBy.value
    }
    const res = await api.getBooks(params)
    books.value = res.list
    total.value = res.total
  } catch (error) {
    console.error('Failed to fetch books:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  if (fullTextSearch.value && keyword.value.trim()) {
    performFullTextSearch()
  } else {
    currentPage.value = 1
    fetchBooks()
  }
}

const handleKeywordChange = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    if (fullTextSearch.value && keyword.value.trim()) {
      performFullTextSearch()
    } else if (!keyword.value) {
      searchResults.value = []
      searchTotal.value = 0
      fetchBooks()
    }
  }, 500)
}

const handleKeywordClear = () => {
  if (searchTimeout) clearTimeout(searchTimeout)
  searchResults.value = []
  searchTotal.value = 0
  fetchBooks()
}

const handleSearchTypeChange = () => {
  if (fullTextSearch.value && keyword.value.trim()) {
    performFullTextSearch()
  } else {
    searchResults.value = []
    fetchBooks()
  }
}

const performFullTextSearch = async () => {
  if (!keyword.value.trim()) {
    searchResults.value = []
    searchTotal.value = 0
    return
  }
  loading.value = true
  try {
    const res = await api.searchBooks(keyword.value.trim(), searchPage.value, searchPageSize.value)
    searchResults.value = res.list || []
    searchTotal.value = res.total || 0
  } catch (error) {
    console.error('Failed to search books:', error)
    searchResults.value = []
    searchTotal.value = 0
  } finally {
    loading.value = false
  }
}

const handleSearchPageChange = (page) => {
  searchPage.value = page
  performFullTextSearch()
}

const backToNormalList = () => {
  fullTextSearch.value = false
  searchResults.value = []
  keyword.value = ''
  currentPage.value = 1
  fetchBooks()
}

const handleTypeChange = (type) => {
  fileType.value = type
  currentPage.value = 1
  fetchBooks()
}

const handleSortChange = () => {
  currentPage.value = 1
  fetchBooks()
}

const handlePageChange = (page) => {
  currentPage.value = page
  fetchBooks()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  fetchBooks()
}

const handleDarkModeChange = (value) => {
  setDarkMode(value)
}

const goToDetail = (bookId) => {
  router.push(`/book/${bookId}`)
}

const goToSearchResult = (item) => {
  const searchParams = {
    fromSearch: '1',
    keyword: keyword.value,
    page: searchPage.value
  }
  if (item.matched_chapter_id) {
    router.push({
      path: `/read/${item.book_id}/${item.matched_chapter_id}`,
      query: { paraId: item.matched_para_id, ...searchParams }
    })
  } else {
    router.push({ path: `/book/${item.book_id}`, query: searchParams })
  }
}

onMounted(() => {
  const savedSettings = JSON.parse(localStorage.getItem('book-list-settings') || '{}')
  if (savedSettings.sortBy) sortBy.value = savedSettings.sortBy
  if (savedSettings.columnsPerRow) columnsPerRow.value = savedSettings.columnsPerRow
  if (savedSettings.viewMode) viewMode.value = savedSettings.viewMode
  if (savedSettings.fileType !== undefined) fileType.value = savedSettings.fileType
  if (savedSettings.keyword) keyword.value = savedSettings.keyword
  if (savedSettings.currentPage) currentPage.value = savedSettings.currentPage
  if (savedSettings.pageSize) pageSize.value = savedSettings.pageSize
  
  if (route.query.fromSearch === '1' && route.query.keyword) {
    keyword.value = route.query.keyword
    searchPage.value = parseInt(route.query.page) || 1
    fullTextSearch.value = true
    performFullTextSearch()
  } else {
    fetchBooks()
  }
  
  fetchReadingHistory()
})

watch([sortBy, columnsPerRow, viewMode, fileType, keyword], () => {
  localStorage.setItem('book-list-settings', JSON.stringify({
    sortBy: sortBy.value,
    columnsPerRow: columnsPerRow.value,
    viewMode: viewMode.value,
    fileType: fileType.value,
    keyword: keyword.value,
    currentPage: currentPage.value,
    pageSize: pageSize.value
  }))
})

watch([currentPage, pageSize], () => {
  const savedSettings = JSON.parse(localStorage.getItem('book-list-settings') || '{}')
  savedSettings.currentPage = currentPage.value
  savedSettings.pageSize = pageSize.value
  localStorage.setItem('book-list-settings', JSON.stringify(savedSettings))
})

const fetchReadingHistory = async () => {
  try {
    const res = await api.getReadingHistory({ page: 1, size: 5 })
    const list = res.data?.list || res.list || []
    readingHistory.value = list.slice(0, 5)
  } catch (error) {
    console.error('Failed to fetch reading history:', error)
  }
}

const clearHistory = async () => {
  try {
    for (const item of readingHistory.value) {
      await api.deleteReadingHistory(item.book_id)
    }
    readingHistory.value = []
  } catch (error) {
    console.error('Failed to clear history:', error)
  }
}

const goToReading = (item) => {
  router.push(`/read/${item.book_id}/${item.chapter_id}`)
}
</script>

<style scoped>
.book-list-page {
  display: flex;
  min-height: 100vh;
  background: var(--bg-color);
}

.sidebar {
  width: 240px;
  background: var(--sidebar-bg);
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  position: fixed;
  height: 100vh;
  border-right: 1px solid var(--border-color);
}

.sidebar-header {
  margin-bottom: 24px;
}

.logo {
  font-size: 20px;
  font-weight: 600;
  color: var(--primary-color);
}

.search-box {
  margin-bottom: 12px;
}

.search-options {
  margin-bottom: 16px;
}

.filter-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: auto;
}

.filter-tag {
  cursor: pointer;
  transition: all 0.3s;
}

.filter-tag:hover {
  transform: translateY(-2px);
}

.reading-history {
  margin-bottom: 20px;
  padding: 12px;
  background: var(--hover-bg);
  border-radius: 8px;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.history-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-item {
  padding: 8px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}

.history-item:hover {
  background: var(--card-bg);
}

.history-book-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-chapter {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-footer {
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.main-content {
  flex: 1;
  margin-left: 240px;
  padding: 24px 32px;
  background: var(--bg-color);
  min-height: 100vh;
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.book-count {
  color: var(--text-secondary);
  font-size: 14px;
}

.book-container {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.book-container.grid-view {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
}

.book-container.cols-3 { grid-template-columns: repeat(3, 1fr); }
.book-container.cols-4 { grid-template-columns: repeat(4, 1fr); }
.book-container.cols-5 { grid-template-columns: repeat(5, 1fr); }
.book-container.cols-6 { grid-template-columns: repeat(6, 1fr); }

.book-container.list-view {
  flex-direction: column;
}

.book-container.list-view .book-card {
  flex-direction: row;
  display: flex;
}

.book-container.list-view .book-cover {
  width: 120px;
  height: 160px;
  flex-shrink: 0;
}

.book-card {
  background: var(--card-bg);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
}

.book-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.book-cover {
  height: 200px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.cover-image {
  max-width: 100%;
  max-height: 100%;
  width: auto;
  height: auto;
  object-fit: contain;
}

.cover-placeholder {
  width: 80px;
  height: 100px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: #667eea;
}

.file-type-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: var(--primary-color);
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
}

.book-info {
  padding: 16px;
}

.book-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #333333;
}

.dark-mode .book-title {
  color: #f0f0f0;
}

.book-author {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.book-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 32px;
  padding-bottom: 32px;
}

@media (max-width: 1920px) {
  .book-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 1440px) {
  .book-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 1080px) {
  .book-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.search-results-container {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-result-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: var(--card-bg);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid var(--border-color);
}

.search-result-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.result-cover {
  flex-shrink: 0;
  width: 100px;
  height: 140px;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.result-cover .cover-image {
  width: 100%;
  height: 100%;
}

.result-cover .cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--hover-bg);
  color: var(--text-secondary);
  font-size: 32px;
}

.result-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
}

.result-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.result-author {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
}

.result-chapter {
  font-size: 13px;
  color: var(--primary-color);
  margin: 4px 0;
  font-weight: 500;
}

.result-snippet {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  padding: 8px;
  background: var(--hover-bg);
  border-radius: 4px;
  margin-top: 8px;
}
</style>
