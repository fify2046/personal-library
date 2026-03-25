<template>
  <div class="book-detail-page" v-loading="loading">
    <div class="detail-container" v-if="book">
      <div class="header-row">
        <el-button class="back-btn" @click="goBack" text>
          <el-icon><ArrowLeft /></el-icon>
          返回列表
        </el-button>
        <el-button type="primary" @click="openEditDialog">
          <el-icon><Edit /></el-icon>
          修改
        </el-button>
      </div>
      
      <div class="book-header">
        <div class="book-cover-large">
          <el-image
            v-if="book.cover_path"
            :src="`/api/images/${encodeURIComponent(book.cover_path)}`"
            fit="cover"
            class="cover-image-large"
          >
            <template #error>
              <div class="cover-placeholder">
                <span class="file-type-badge">{{ book.file_type.toUpperCase() }}</span>
              </div>
            </template>
          </el-image>
          <div v-else class="cover-placeholder">
            <span class="file-type-badge">{{ book.file_type.toUpperCase() }}</span>
          </div>
        </div>
        
        <div class="book-info">
          <h1 class="book-title">{{ book.title }}</h1>
          <div class="book-meta">
            <div class="meta-item">
              <span class="label">作者</span>
              <span class="value">{{ book.author || '未知' }}</span>
            </div>
            <div class="meta-item" v-if="book.publisher">
              <span class="label">出版社</span>
              <span class="value">{{ book.publisher }}</span>
            </div>
            <div class="meta-item" v-if="book.publish_date">
              <span class="label">出版日期</span>
              <span class="value">{{ book.publish_date }}</span>
            </div>
            <div class="meta-item">
              <span class="label">评分</span>
              <span class="value">
                <el-rate 
                  v-model="bookRating" 
                  :allow-half="true"
                  :max="5"
                  @change="handleRatingChange"
                />
                <span class="rating-text">{{ bookRating > 0 ? bookRating + '星' : '未评分' }}</span>
              </span>
            </div>
            <div class="meta-item">
              <span class="label">格式</span>
              <span class="value">{{ book.file_type.toUpperCase() }}</span>
            </div>
            <div class="meta-item">
              <span class="label">文件大小</span>
              <span class="value">{{ formatFileSize(book.file_size) }}</span>
            </div>
            <div class="meta-item">
              <span class="label">章节数</span>
              <span class="value">{{ book.chapter_count }} 章</span>
            </div>
            <div class="meta-item">
              <span class="label">图片数</span>
              <span class="value">{{ book.image_count }} 张</span>
            </div>
          </div>
          
          <div class="action-buttons-row">
            <el-button
              type="primary"
              size="large"
              class="start-reading-btn"
              @click="startReading"
            >
              {{ hasReadingProgress ? '继续阅读' : '开始阅读' }}
            </el-button>

            <el-button
              :type="inReadingList ? 'info' : 'default'"
              size="large"
              @click="toggleReadingList"
            >
              <el-icon><Reading /></el-icon>
              {{ inReadingList ? '已加入阅读列表' : '添加到阅读列表' }}
            </el-button>

            <el-button
              v-if="aiEnabled"
              type="success"
              size="large"
              @click="showAISummaryDialog"
            >
              <el-icon><MagicStick /></el-icon>
              AI辅助阅读
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="aiSummaryDialogVisible" title="AI辅助阅读 - 选择章节生成摘要" width="700px">
      <el-alert
        title="操作说明"
        type="info"
        :closable="false"
        style="margin-bottom: 20px;"
      >
        勾选需要生成AI摘要的章节，然后点击"生成AI摘要"按钮。已生成摘要的章节会显示绿色标记。
      </el-alert>

      <div style="max-height: 400px; overflow-y: auto;">
        <el-tree
          :data="chapterTreeData"
          :props="{ label: 'label', children: 'children' }"
          node-key="id"
          show-checkbox
          default-expand-all
          ref="chapterTreeRef"
        >
          <template #default="{ node, data }">
            <span class="chapter-tree-node">
              <span>{{ node.label }}</span>
              <el-tag v-if="data.hasSummary" type="success" size="small" style="margin-left: 8px;">已生成</el-tag>
            </span>
          </template>
        </el-tree>
      </div>

      <template #footer>
        <el-button @click="aiSummaryDialogVisible = false">取消</el-button>
        <el-button @click="selectAllChapters">全选</el-button>
        <el-button @click="deselectAllChapters">取消全选</el-button>
        <el-button type="primary" @click="generateAISummary" :loading="generatingSummary">
          生成AI摘要
        </el-button>
      </template>
    </el-dialog>
    
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
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Reading, Edit, MagicStick } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api.js'

const router = useRouter()
const route = useRoute()

const book = ref(null)
const loading = ref(false)
const chapters = ref([])
const inReadingList = ref(false)
const hasReadingProgress = ref(false)
const lastChapterId = ref(null)
const bookRating = ref(0)
const editDialogVisible = ref(false)
const aiEnabled = ref(false)
const aiSummaryDialogVisible = ref(false)
const generatingSummary = ref(false)
const chapterTreeRef = ref(null)
const chapterSummaries = ref({})
const aiTimeout = ref(120000)
const editForm = ref({
  title: '',
  author: '',
  publisher: '',
  publish_date: '',
  isbn: ''
})

const openEditDialog = () => {
  editForm.value = {
    title: book.value.title || '',
    author: book.value.author || '',
    publisher: book.value.publisher || '',
    publish_date: book.value.publish_date || '',
    isbn: book.value.isbn || ''
  }
  editDialogVisible.value = true
}

const saveEdit = async () => {
  try {
    await api.updateBook(book.value.book_id, {
      title: editForm.value.title,
      author: editForm.value.author,
      publisher: editForm.value.publisher,
      publish_date: editForm.value.publish_date,
      isbn: editForm.value.isbn
    })
    book.value.title = editForm.value.title
    book.value.author = editForm.value.author
    book.value.publisher = editForm.value.publisher
    book.value.publish_date = editForm.value.publish_date
    book.value.isbn = editForm.value.isbn
    ElMessage.success('修改成功')
    editDialogVisible.value = false
  } catch (error) {
    ElMessage.error('修改失败')
  }
}

const fetchBookDetail = async () => {
  loading.value = true
  try {
    const bookId = route.params.id
    book.value = await api.getBook(bookId)
    bookRating.value = (book.value.rating || 0) / 2
    chapters.value = await api.getChapters(bookId)
    
    const [listRes, progressRes] = await Promise.all([
      api.checkInReadingList(bookId).catch(() => ({ data: { in_list: false } })),
      api.getReadingProgress(bookId).catch(() => ({ code: 404 }))
    ])
    
    inReadingList.value = listRes.data?.in_list || false
    
    if (progressRes.code === 200 && progressRes.data) {
      hasReadingProgress.value = true
      lastChapterId.value = progressRes.data.chapter_id
    }
  } catch (error) {
    console.error('Failed to fetch book detail:', error)
    ElMessage.error('获取书籍详情失败')
  } finally {
    loading.value = false
  }
}

const formatFileSize = (bytes) => {
  if (!bytes) return '未知'
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + sizes[i]
}

const goBack = () => {
  const returnPath = sessionStorage.getItem('returnPath')
  sessionStorage.removeItem('returnPath')
  if (returnPath) {
    router.push(returnPath)
  } else {
    router.push('/')
  }
}

const startReading = () => {
  if (hasReadingProgress.value && lastChapterId.value) {
    router.push(`/read/${book.value.book_id}/${lastChapterId.value}`)
  } else if (chapters.value.length > 0) {
    router.push(`/read/${book.value.book_id}/${chapters.value[0].chapter_id}`)
  } else {
    ElMessage.warning('该书暂无章节内容')
  }
}

const handleRatingChange = async (rating) => {
  const bookId = book.value.book_id
  const ratingValue = Math.round(rating * 2)
  try {
    await api.setBookRating(bookId, ratingValue)
    book.value.rating = ratingValue
    ElMessage.success('评分已保存')
  } catch (error) {
    ElMessage.error('评分保存失败')
  }
}

const toggleReadingList = async () => {
  const bookId = book.value.book_id
  try {
    if (inReadingList.value) {
      await api.removeFromReadingList(bookId)
      ElMessage.success('已从阅读列表中移除')
      inReadingList.value = false
    } else {
      await api.addToReadingList(bookId)
      ElMessage.success('已添加到阅读列表')
      inReadingList.value = true
    }
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

const checkAIStatus = async () => {
  try {
    const status = await api.getAIStatus()
    aiEnabled.value = status.ai_enabled
    aiTimeout.value = status.timeout || 120000
  } catch (error) {
    aiEnabled.value = false
  }
}

const showAISummaryDialog = async () => {
  aiSummaryDialogVisible.value = true
  await loadChapterSummaries()
}

const loadChapterSummaries = async () => {
  try {
    for (const chapter of chapters.value) {
      try {
        const summary = await api.getChapterSummary(chapter.chapter_id)
        chapterSummaries.value[chapter.chapter_id] = summary
      } catch (error) {
        chapterSummaries.value[chapter.chapter_id] = null
      }
    }
  } catch (error) {
    console.error('Failed to load chapter summaries:', error)
  }
}

const chapterTreeData = computed(() => {
  const buildTree = (parentId = null) => {
    return chapters.value
      .filter(ch => ch.parent_id === parentId)
      .map(ch => {
        const children = buildTree(ch.chapter_id)
        return {
          id: ch.chapter_id,
          label: ch.chapter_name || `第${ch.chapter_order}章`,
          hasSummary: !!chapterSummaries.value[ch.chapter_id],
          children: children.length > 0 ? children : null
        }
      })
  }
  return buildTree()
})

const selectAllChapters = () => {
  if (chapterTreeRef.value) {
    const allIds = chapters.value.map(ch => ch.chapter_id)
    chapterTreeRef.value.setCheckedKeys(allIds)
  }
}

const deselectAllChapters = () => {
  if (chapterTreeRef.value) {
    chapterTreeRef.value.setCheckedKeys([])
  }
}

const generateAISummary = async () => {
  if (!chapterTreeRef.value) return

  const checkedNodes = chapterTreeRef.value.getCheckedNodes()
  const chapterIds = checkedNodes.map(node => node.id)

  if (chapterIds.length === 0) {
    ElMessage.warning('请至少选择一个章节')
    return
  }

  try {
    generatingSummary.value = true
    const result = await api.generateSummary(chapterIds, null, aiTimeout.value)

    if (result.success) {
      ElMessage.success(result.message)
      await loadChapterSummaries()
    } else {
      ElMessage.warning(result.message)
    }
  } catch (error) {
    ElMessage.error('生成摘要失败')
    console.error(error)
  } finally {
    generatingSummary.value = false
  }
}

onMounted(() => {
  fetchBookDetail()
  checkAIStatus()
})
</script>

<style scoped>
.book-detail-page {
  min-height: 100vh;
  background: var(--bg-color);
  padding: 24px;
}

.detail-container {
  max-width: 900px;
  margin: 0 auto;
}

.back-btn {
  margin-bottom: 24px;
  color: var(--text-secondary);
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.book-header {
  display: flex;
  gap: 40px;
  background: var(--card-bg);
  padding: 40px;
  border-radius: 16px;
  box-shadow: var(--shadow);
}

.book-cover-large {
  width: 240px;
  height: 320px;
  flex-shrink: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.cover-image-large {
  width: 100%;
  height: 100%;
  border-radius: 12px;
}

.cover-placeholder {
  width: 140px;
  height: 180px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.file-type-badge {
  position: absolute;
  top: 12px;
  right: 12px;
  background: var(--primary-color);
  color: white;
  font-size: 14px;
  padding: 4px 10px;
  border-radius: 6px;
}

.book-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.book-title {
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 24px;
  color: var(--text-primary);
}

.book-meta {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 32px;
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.label {
  font-size: 14px;
  color: var(--text-secondary);
}

.value {
  font-size: 16px;
  color: var(--text-primary);
  font-weight: 500;
}

.start-reading-btn {
  align-self: flex-start;
  padding: 16px 48px;
  font-size: 18px;
  border-radius: 8px;
}

.action-buttons-row {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

@media (max-width: 768px) {
  .book-header {
    flex-direction: column;
    align-items: center;
  }
  
  .book-meta {
    grid-template-columns: 1fr;
  }
}

.rating-text {
  margin-left: 8px;
  color: var(--text-secondary);
  font-size: 14px;
}

.chapter-tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
</style>
