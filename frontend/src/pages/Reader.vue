<template>
  <div class="reader-page">
    <aside class="chapter-sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <h3>{{ sidebarCollapsed ? '' : '目录' }}</h3>
        <div class="header-actions">
          <template v-if="!sidebarCollapsed">
            <el-tooltip content="全部展开" placement="bottom">
              <el-button text @click="expandAllChapters" :icon="CaretBottom" />
            </el-tooltip>
            <el-tooltip content="全部收缩" placement="bottom">
              <el-button text @click="collapseAllChapters" :icon="CaretRight" />
            </el-tooltip>
          </template>
          <el-button 
            :icon="sidebarCollapsed ? Expand : Fold" 
            text 
            @click="sidebarCollapsed = !sidebarCollapsed"
            class="collapse-btn"
          />
        </div>
      </div>
      
      <div class="chapter-search" v-if="!sidebarCollapsed">
        <el-input
          v-model="chapterSearch"
          placeholder="搜索章节..."
          clearable
          size="small"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
      
      <div class="chapter-list" v-if="!sidebarCollapsed">
        <template v-for="chapter in filteredChapters" :key="chapter.chapter_id">
          <div 
            class="chapter-item"
            :class="[
              { active: chapter.chapter_id === currentChapterId },
              { 'has-children': chapter.children && chapter.children.length > 0 },
              'level-' + chapter.chapter_level
            ]"
            :style="{ paddingLeft: (16 + chapter.chapter_level * 16) + 'px' }"
          >
            <span 
              v-if="chapter.children && chapter.children.length > 0"
              class="expand-icon"
              @click.stop="toggleChapterExpand(chapter)"
            >
              <el-icon :class="{ expanded: chapter.expanded }"><ArrowRight /></el-icon>
            </span>
            <span v-else class="expand-placeholder"></span>
            <span class="chapter-name" @click="goToChapter(chapter)">{{ chapter.chapter_name }}</span>
          </div>
          <template v-if="chapter.expanded && chapter.children">
            <template v-for="child in chapter.children" :key="child.chapter_id">
              <div 
                class="chapter-item"
                :class="[
                  { active: child.chapter_id === currentChapterId },
                  { 'has-children': child.children && child.children.length > 0 },
                  'level-' + child.chapter_level
                ]"
                :style="{ paddingLeft: (16 + child.chapter_level * 16) + 'px' }"
              >
                <span 
                  v-if="child.children && child.children.length > 0"
                  class="expand-icon"
                  @click.stop="toggleChapterExpand(child)"
                >
                  <el-icon :class="{ expanded: child.expanded }"><ArrowRight /></el-icon>
                </span>
                <span v-else class="expand-placeholder"></span>
                <span class="chapter-name" @click="goToChapter(child)">{{ child.chapter_name }}</span>
              </div>
              <template v-if="child.expanded && child.children">
                <div 
                  v-for="grandchild in child.children" 
                  :key="grandchild.chapter_id"
                  class="chapter-item"
                  :class="[
                    { active: grandchild.chapter_id === currentChapterId },
                    'level-' + grandchild.chapter_level
                  ]"
                  :style="{ paddingLeft: (16 + grandchild.chapter_level * 16) + 'px' }"
                >
                  <span class="expand-placeholder"></span>
                  <span class="chapter-name" @click="goToChapter(grandchild)">{{ grandchild.chapter_name }}</span>
                </div>
              </template>
            </template>
          </template>
        </template>
      </div>
    </aside>
    
    <main class="reader-main">
      <header class="toolbar">
        <div class="toolbar-left">
          <el-button :icon="Back" circle @click="goBack" />
          <span class="book-title">{{ bookTitle }}</span>
        </div>
        
        <div class="toolbar-right">
          <el-button-group>
            <el-button :icon="Minus" circle @click="decreaseFontSize" title="减小字体" />
            <el-button :icon="Plus" circle @click="increaseFontSize" title="增大字体" />
          </el-button-group>
          
          <el-button :icon="Document" circle @click="cycleLineHeight" title="行间距" />
          
          <el-button circle @click="toggleTraditional" :class="{ active: isTraditional }" title="繁简转换">
            {{ isTraditional ? '繁' : '简' }}
          </el-button>
          
          <el-switch
            v-model="isDark"
            @change="handleDarkModeChange"
            active-text="暗"
            inactive-text="亮"
          />
          
          <el-button :icon="Picture" circle @click="toggleImageFit" :class="{ active: imageFit }" title="图片自适应" />

          <el-button
            v-if="aiEnabled"
            type="primary"
            @click="toggleAISummary"
            :class="{ active: showAISummary }"
            title="AI摘要"
          >
            <el-icon><MagicStick /></el-icon>
            AI摘要
          </el-button>
          <el-dropdown v-if="aiEnabled && showAISummary" @command="handleTemplateChange">
            <el-button type="default">
              {{ selectedTemplateName || '选择模板' }}
              <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="">默认提示词</el-dropdown-item>
                <el-dropdown-item
                  v-for="template in promptTemplates"
                  :key="template.name"
                  :command="template.name"
                >
                  {{ template.name }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button
            v-if="aiEnabled && showAISummary"
            circle
            @click="toggleSummaryPosition"
            :title="summaryPosition === 'right' ? '切换到左侧' : '切换到右侧'"
          >
            <el-icon><Switch /></el-icon>
          </el-button>
        </div>
      </header>

      <aside class="ai-summary-panel" v-if="showAISummary && aiEnabled" :class="{ 'summary-left': summaryPosition === 'left' }">
        <div class="ai-summary-header">
          <h3>AI摘要</h3>
          <el-button text @click="showAISummary = false">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
        <div class="ai-summary-content" v-loading="aiSummaryLoading">
          <div v-if="aiSummaryContent" class="summary-text">
            <div style="margin-bottom: 12px; text-align: center;">
              <el-button size="small" type="warning" @click="generateAISummary">
                重新生成
              </el-button>
            </div>
            <div class="markdown-body" v-html="renderedSummary"></div>
          </div>
          <div v-else-if="!aiSummaryLoading" class="no-summary">
            <p>暂无AI摘要</p>
            <el-button size="small" type="primary" @click="generateAISummary">
              生成AI摘要
            </el-button>
          </div>
        </div>
      </aside>
      
      <div class="reading-progress" v-if="flatChapters.length > 0">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
        <span class="progress-text">{{ currentChapterIndex + 1 }} / {{ flatChapters.length }}</span>
      </div>
      
      <div
        class="content-area"
        :class="{ 'with-summary': showAISummary && aiEnabled, 'summary-left': summaryPosition === 'left' }"
        :style="{ fontSize: fontSize + 'px', lineHeight: lineHeight }"
        ref="contentRef"
        @mousemove="handleContentMouseMove"
        @mouseleave="handleContentMouseLeave"
      >
        <div 
          class="side-arrow left-arrow" 
          :class="{ visible: showLeftArrow }"
          :style="{ left: leftArrowPos + 'px' }"
          @click="prevChapter"
        >
          <el-icon><ArrowLeft /></el-icon>
        </div>
        
        <h1 class="chapter-title">{{ convertedChapterName || chapterName }}</h1>
        
        <template v-for="item in (convertedContent.length > 0 ? convertedContent : content)" :key="item.id">
          <p v-if="item.type === 'text' && !item.is_footnote" class="paragraph" :data-para-id="item.id" v-html="formatText(item.content)"></p>
          <div v-else-if="item.type === 'image'" class="image-container" :class="{ 'full-width': !imageFit }">
            <el-image
              :src="getImageUrl(item.content)"
              :preview-src-list="[getImageUrl(item.content)]"
              :fit="imageFit ? 'contain' : 'cover'"
              class="content-image"
              :preview-teleported="true"
            />
          </div>
          <table v-else-if="item.type === 'table'" class="content-table">
            <thead v-if="getTableData(item.content).headers && getTableData(item.content).headers.length > 0">
              <tr>
                <th v-for="(header, idx) in getTableData(item.content).headers" :key="'h'+idx">{{ header }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, rowIdx) in getTableData(item.content).rows" :key="'r'+rowIdx">
                <td v-for="(cell, cellIdx) in row" :key="'c'+cellIdx">{{ cell }}</td>
              </tr>
            </tbody>
          </table>
        </template>
        
        <div v-if="chapterFootnotes.length > 0" class="footnotes-section">
          <h3 class="footnotes-title">注释</h3>
          <div class="footnotes-list">
            <div 
              v-for="(footnote, idx) in chapterFootnotes" 
              :key="footnote.id"
              :id="'footnote-' + (idx + 1)"
              class="footnote-item"
            >
              <span class="footnote-number">[{{ idx + 1 }}]</span>
              <span class="footnote-text">{{ footnote.content }}</span>
            </div>
          </div>
        </div>
        
        <div 
          class="side-arrow right-arrow" 
          :class="{ visible: showRightArrow }"
          :style="{ right: rightArrowPos + 'px' }"
          @click="nextChapter"
        >
          <el-icon><ArrowRight /></el-icon>
        </div>
      </div>
      
      <footer class="bottom-nav">
        <el-button 
          :disabled="currentChapterIndex === 0"
          @click="prevChapter"
        >
          <el-icon><ArrowLeft /></el-icon>
          上一章
        </el-button>
        
        <el-button circle @click="scrollToTop" title="回到顶部">
          <el-icon><Top /></el-icon>
        </el-button>
        
        <el-button 
          :disabled="currentChapterIndex === flatChapters.length - 1"
          @click="nextChapter"
        >
          下一章
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </footer>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, inject, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  Search, Back, Minus, Plus, Document, Picture,
  ArrowLeft, ArrowRight, Top, Expand, Fold, CaretRight, CaretBottom, MagicStick, Close, ArrowDown, Switch
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api.js'
import * as OpenCC from 'opencc-js'
import { marked } from 'marked'

const router = useRouter()
const route = useRoute()

let converterTWtoCN = null
let converterCNtoTW = null
let converterHKtoCN = null
let converterCNtoHK = null
let converterReady = false

const initConverter = async () => {
  if (!converterTWtoCN) {
    converterTWtoCN = OpenCC.Converter({ from: 'tw', to: 'cn' })
  }
  if (!converterCNtoTW) {
    converterCNtoTW = OpenCC.Converter({ from: 'cn', to: 'tw' })
  }
  if (!converterHKtoCN) {
    converterHKtoCN = OpenCC.Converter({ from: 'hk', to: 'cn' })
  }
  if (!converterCNtoHK) {
    converterCNtoHK = OpenCC.Converter({ from: 'cn', to: 'hk' })
  }
  converterReady = true
}

initConverter()

const bookTitle = ref('')
const chapters = ref([])
const currentChapterId = ref(null)
const currentChapterIndex = ref(0)
const chapterName = ref('')
const content = ref([])
const sidebarCollapsed = ref(false)
const chapterSearch = ref('')
const contentRef = ref(null)
const imageFit = ref(true)
const isTraditional = ref(false)
const showLeftArrow = ref(false)
const showRightArrow = ref(false)

const aiEnabled = ref(false)
const showAISummary = ref(false)
const aiSummaryContent = ref('')
const aiSummaryLoading = ref(false)
const aiTimeout = ref(120000)
const promptTemplates = ref([])
const selectedTemplateName = ref('')
const summaryPosition = ref('right')

const renderedSummary = computed(() => {
  if (!aiSummaryContent.value) return ''
  return marked(aiSummaryContent.value)
})

const fontSize = inject('fontSize')
const lineHeight = inject('lineHeight')
const isDarkMode = inject('isDarkMode')
const setDarkMode = inject('setDarkMode')
const setFontSize = inject('setFontSize')
const setLineHeight = inject('setLineHeight')

const isDark = computed({
  get: () => isDarkMode.value,
  set: (val) => setDarkMode(val)
})

const flattenChapters = (chapterList, result = []) => {
  for (const chapter of chapterList) {
    result.push(chapter)
    if (chapter.children && chapter.children.length > 0) {
      flattenChapters(chapter.children, result)
    }
  }
  return result
}

const flatChapters = computed(() => flattenChapters(chapters.value))

const totalChapters = computed(() => flatChapters.value.length)

const currentChapter = computed(() => flatChapters.value[currentChapterIndex.value])

const progressPercent = computed(() => {
  if (totalChapters.value === 0) return 0
  return ((currentChapterIndex.value + 1) / totalChapters.value) * 100
})

const chapterFootnotes = computed(() => {
  const footnotes = []
  const contentToUse = convertedContent.value.length > 0 ? convertedContent.value : content.value
  for (const item of contentToUse) {
    if (item.type === 'text' && item.is_footnote) {
      footnotes.push(item)
    }
  }
  return footnotes
})

const filterChapters = (chapterList, keyword) => {
  const result = []
  for (const chapter of chapterList) {
    const matchesKeyword = !keyword || (chapter.chapter_name && chapter.chapter_name.toLowerCase().includes(keyword))
    const hasMatchingChildren = chapter.children && chapter.children.length > 0 && filterChapters(chapter.children, keyword).length > 0
    
    if (matchesKeyword || hasMatchingChildren) {
      const newChapter = { ...chapter }
      if (chapter.children && chapter.children.length > 0) {
        newChapter.children = filterChapters(chapter.children, keyword)
        if (hasMatchingChildren) {
          newChapter.expanded = true
        }
      }
      result.push(newChapter)
    }
  }
  return result
}

const filteredChapters = computed(() => {
  if (!chapterSearch.value) return chapters.value
  const keyword = chapterSearch.value.toLowerCase()
  return filterChapters(chapters.value, keyword)
})

const convertedContent = ref([])
const convertedChapterName = ref('')

const convertContent = () => {
  if (!converterTWtoCN || !converterCNtoTW || !converterHKtoCN || !converterCNtoHK) {
    initConverter()
  }
  
  if (!isTraditional.value) {
    const newContent = []
    for (const item of content.value) {
      if (item.type === 'text') {
        newContent.push({
          ...item,
          content: converterHKtoCN(item.content)
        })
      } else {
        newContent.push(item)
      }
    }
    convertedContent.value = newContent
    convertedChapterName.value = converterHKtoCN(chapterName.value)
  } else {
    const newContent = []
    for (const item of content.value) {
      if (item.type === 'text') {
        newContent.push({
          ...item,
          content: converterCNtoHK(item.content)
        })
      } else {
        newContent.push(item)
      }
    }
    convertedContent.value = newContent
    convertedChapterName.value = converterCNtoHK(chapterName.value)
  }
}

watch(isTraditional, () => {
  convertContent()
})

watch(content, () => {
  convertContent()
}, { deep: true })

watch(sidebarCollapsed, () => {
  if (contentRef.value) {
    const rect = contentRef.value.getBoundingClientRect()
    leftArrowPos.value = rect.left + 10
    rightArrowPos.value = window.innerWidth - rect.right + 10
  }
})

const fetchBookInfo = async () => {
  try {
    const bookId = route.params.bookId
    const book = await api.getBook(bookId)
    bookTitle.value = book.title
  } catch (error) {
    console.error('Failed to fetch book info:', error)
  }
}

const isTraditionalContent = (text) => {
  const traditionalChars = ['為', '說', '國', '時', '應該', '與', '這', '裡', '後', '發', '會', '種', '還', '麼', '過', '兩個', '沒有', '什麼', '這個', '那個', '已經', '因為', '所以', '但是', '可以', '自己', '這樣', '那樣', '這裡', '那裡']
  for (const char of traditionalChars) {
    if (text.includes(char)) return true
  }
  return false
}

const loadDisplayMode = async () => {
  try {
    const bookId = route.params.bookId
    const res = await api.getDisplayMode(bookId)
    let mode = res.data?.display_mode || 'original'
    
    if (mode === 'original' && content.value.length > 0) {
      let sampleText = ''
      for (const item of content.value.slice(0, 10)) {
        if (item.type === 'text') {
          sampleText += item.content
          if (sampleText.length > 500) break
        }
      }
      if (isTraditionalContent(sampleText)) {
        mode = 'traditional'
      }
    }
    
    isTraditional.value = mode === 'traditional'
    convertContent()
  } catch (e) {
    console.error('加载显示模式失败:', e)
  }
}

const fetchChapters = async () => {
  try {
    const bookId = route.params.bookId
    chapters.value = await api.getChapters(bookId)
    
    const savedChapterId = route.params.chapterId
    if (savedChapterId) {
      const idx = flatChapters.value.findIndex(c => c.chapter_id === savedChapterId)
      if (idx !== -1) {
        currentChapterIndex.value = idx
      }
    }
    
    if (flatChapters.value.length > 0 && !route.params.chapterId) {
      currentChapterIndex.value = 0
    }
    
    await fetchChapterContent()
    await saveReadingProgress()
    expandChapterToCurrent(flatChapters.value[currentChapterIndex.value]?.chapter_id)
  } catch (error) {
    console.error('Failed to fetch chapters:', error)
  }
}

const fetchChapterContent = async () => {
  if (flatChapters.value.length === 0) return

  const chapter = flatChapters.value[currentChapterIndex.value]
  if (!chapter) return

  currentChapterId.value = chapter.chapter_id
  chapterName.value = chapter.chapter_name

  try {
    const res = await api.getChapterContent(chapter.chapter_id)
    content.value = res.content
    convertContent()

    await nextTick()
    const targetParaId = route.query.paraId
    if (targetParaId) {
      const targetElement = document.querySelector(`[data-para-id="${targetParaId}"]`)
      if (targetElement) {
        targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
        targetElement.classList.add('highlight-para')
        setTimeout(() => {
          targetElement.classList.remove('highlight-para')
        }, 3000)
      }
    }

    if (showAISummary.value && aiEnabled.value) {
      await loadAISummary()
    }
  } catch (error) {
    console.error('Failed to fetch chapter content:', error)
    content.value = []
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

const loadPromptTemplates = async () => {
  try {
    const templates = await api.getPromptTemplates()
    promptTemplates.value = templates || []
  } catch (error) {
    console.error('加载提示词模板失败:', error)
    promptTemplates.value = []
  }
}

const loadLocalSettings = () => {
  const settings = api.getLocalAISettings()
  selectedTemplateName.value = settings.templateName || ''
  summaryPosition.value = settings.summaryPosition || 'right'
}

const saveLocalSettings = () => {
  api.setLocalAISettings({
    templateName: selectedTemplateName.value,
    summaryPosition: summaryPosition.value
  })
}

const handleTemplateChange = (templateName) => {
  selectedTemplateName.value = templateName
  saveLocalSettings()
}

const toggleSummaryPosition = () => {
  summaryPosition.value = summaryPosition.value === 'right' ? 'left' : 'right'
  saveLocalSettings()
}

const toggleAISummary = () => {
  showAISummary.value = !showAISummary.value
  if (showAISummary.value && aiEnabled.value && !aiSummaryContent.value) {
    loadAISummary()
  }
}

const loadAISummary = async () => {
  if (!currentChapterId.value) return

  try {
    aiSummaryLoading.value = true
    const summary = await api.getChapterSummary(currentChapterId.value)
    aiSummaryContent.value = summary.summary_content
  } catch (error) {
    aiSummaryContent.value = ''
  } finally {
    aiSummaryLoading.value = false
  }
}

const generateAISummary = async () => {
  if (!currentChapterId.value) return

  try {
    aiSummaryLoading.value = true
    const result = await api.generateSummary([currentChapterId.value], null, aiTimeout.value, selectedTemplateName.value || null)
    if (result.success) {
      ElMessage.success('AI摘要生成成功')
      await loadAISummary()
    } else {
      ElMessage.warning(result.message)
    }
  } catch (error) {
    ElMessage.error('生成AI摘要失败')
    console.error(error)
  } finally {
    aiSummaryLoading.value = false
  }
}

const saveReadingProgress = async () => {
  if (!currentChapter.value) return
  try {
    await api.saveReadingProgress({
      book_id: route.params.bookId,
      chapter_id: currentChapter.value.chapter_id,
      chapter_name: currentChapter.value.chapter_name,
      book_title: bookTitle.value
    })
  } catch (error) {
    console.error('Failed to save reading progress:', error)
  }
}

const toggleChapterExpand = (chapter) => {
  chapter.expanded = !chapter.expanded
}

const expandAllChapters = () => {
  const setExpanded = (chapterList, expanded) => {
    chapterList.forEach(chapter => {
      if (chapter.children && chapter.children.length > 0) {
        chapter.expanded = expanded
        setExpanded(chapter.children, expanded)
      }
    })
  }
  setExpanded(chapters.value, true)
}

const collapseAllChapters = () => {
  const setExpanded = (chapterList, expanded) => {
    chapterList.forEach(chapter => {
      if (chapter.children && chapter.children.length > 0) {
        chapter.expanded = expanded
        setExpanded(chapter.children, expanded)
      }
    })
  }
  setExpanded(chapters.value, false)
}

const expandChapterToCurrent = (chapterId) => {
  const findAndExpand = (chapterList) => {
    for (const chapter of chapterList) {
      if (chapter.chapter_id === chapterId) {
        return true
      }
      if (chapter.children && chapter.children.length > 0) {
        if (findAndExpand(chapter.children)) {
          chapter.expanded = true
          return true
        }
      }
    }
    return false
  }
  findAndExpand(chapters.value)
}

const goToChapter = (chapter) => {
  const idx = flatChapters.value.findIndex(c => c.chapter_id === chapter.chapter_id)
  if (idx !== -1) {
    currentChapterIndex.value = idx
    fetchChapterContent()
    saveReadingProgress()
    expandChapterToCurrent(chapter.chapter_id)
    scrollToTop()
  }
}

const prevChapter = () => {
  if (currentChapterIndex.value > 0) {
    currentChapterIndex.value--
    fetchChapterContent()
    saveReadingProgress()
    expandChapterToCurrent(flatChapters.value[currentChapterIndex.value]?.chapter_id)
    scrollToTop()
  }
}

const nextChapter = () => {
  if (currentChapterIndex.value < flatChapters.value.length - 1) {
    currentChapterIndex.value++
    fetchChapterContent()
    saveReadingProgress()
    expandChapterToCurrent(flatChapters.value[currentChapterIndex.value]?.chapter_id)
    scrollToTop()
  }
}

const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const handleContentMouseMove = (e) => {
  const contentArea = e.currentTarget
  const rect = contentArea.getBoundingClientRect()
  const x = e.clientX - rect.left
  const width = rect.width
  const threshold = width * 0.1
  
  showLeftArrow.value = x < threshold && currentChapterIndex.value > 0
  showRightArrow.value = x > width - threshold && currentChapterIndex.value < flatChapters.value.length - 1
  
  leftArrowPos.value = sidebarCollapsed.value ? rect.left + 10 : rect.left + 10
  rightArrowPos.value = sidebarCollapsed.value ? window.innerWidth - rect.right + 10 : window.innerWidth - rect.right + 10
}

const leftArrowPos = ref(250)
const rightArrowPos = ref(10)

const handleContentMouseLeave = () => {
  showLeftArrow.value = false
  showRightArrow.value = false
}

const goBack = () => {
  if (route.query.fromSearch === '1') {
    router.push({
      path: '/',
      query: {
        fromSearch: '1',
        keyword: route.query.keyword,
        page: route.query.page
      }
    })
  } else {
    router.push(`/book/${route.params.bookId}`)
  }
}

const increaseFontSize = () => {
  setFontSize(fontSize.value + 2)
}

const decreaseFontSize = () => {
  setFontSize(fontSize.value - 2)
}

const cycleLineHeight = () => {
  const heights = [1.8, 2.0, 2.2, 1.6]
  const currentIdx = heights.indexOf(lineHeight.value)
  const nextIdx = (currentIdx + 1) % heights.length
  setLineHeight(heights[nextIdx])
}

const toggleImageFit = () => {
  imageFit.value = !imageFit.value
}

const handleDarkModeChange = (val) => {
  setDarkMode(val)
}

const getImageUrl = (path) => {
  return `/api/images/${encodeURIComponent(path)}`
}

const formatText = (text) => {
  if (!text) return ''
  let result = text
  result = result.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  result = result.replace(/\*(.+?)\*/g, '<em>$1</em>')
  result = result.replace(/\^\[(\d+)\]\^/g, '<a href="#footnote-$1" class="footnote-ref">[$1]</a>')
  result = result.replace(/\^(.+?)\^/g, '<sup class="sup-text">$1</sup>')
  result = result.replace(/~(.+?)~/g, '<sub>$1</sub>')
  return result
}

const getTableData = (content) => {
  try {
    if (typeof content === 'string') {
      return JSON.parse(content)
    }
    return content || { headers: [], rows: [] }
  } catch (e) {
    console.error('解析表格数据失败:', e)
    return { headers: [], rows: [] }
  }
}

const toggleTraditional = async () => {
  isTraditional.value = !isTraditional.value
  
  if (!converterTWtoCN || !converterCNtoTW || !converterHKtoCN || !converterCNtoHK) {
    initConverter()
  }
  convertContent()
  
  const bookId = route.params.bookId
  const mode = isTraditional.value ? 'traditional' : 'original'
  try {
    await api.setDisplayMode(bookId, mode)
  } catch (e) {
    console.error('保存显示模式失败:', e)
  }
}

const handleKeydown = (e) => {
  if (e.key === 'ArrowLeft') {
    prevChapter()
  } else if (e.key === 'ArrowRight') {
    nextChapter()
  } else if (e.ctrlKey && e.key === '=') {
    e.preventDefault()
    increaseFontSize()
  } else if (e.ctrlKey && e.key === '-') {
    e.preventDefault()
    decreaseFontSize()
  }
}

onMounted(() => {
  fetchBookInfo()
  fetchChapters()
  loadDisplayMode()
  checkAIStatus()
  loadPromptTemplates()
  loadLocalSettings()
  window.addEventListener('keydown', handleKeydown)

  setTimeout(() => {
    if (contentRef.value) {
      const rect = contentRef.value.getBoundingClientRect()
      leftArrowPos.value = rect.left + 10
      rightArrowPos.value = window.innerWidth - rect.right + 10
    }
  }, 100)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})

watch(() => route.params.bookId, () => {
  fetchBookInfo()
  fetchChapters()
  loadDisplayMode()
})
</script>

<style scoped>
.reader-page {
  display: flex;
  min-height: 100vh;
  background: var(--bg-color);
}

.chapter-sidebar {
  width: 300px;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  position: fixed;
  height: 100vh;
  transition: width 0.3s;
  z-index: 100;
}

.chapter-sidebar.collapsed {
  width: 60px;
}

.sidebar-header {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
}

.sidebar-header h3 {
  margin: 0;
  font-size: 18px;
  color: var(--text-primary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.collapse-btn {
  color: var(--text-secondary);
}

.chapter-search {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-color);
}

.chapter-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.chapter-item {
  padding: 10px 16px;
  cursor: pointer;
  border-radius: 8px;
  font-size: 14px;
  color: var(--text-primary);
  transition: all 0.2s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  gap: 4px;
}

.chapter-item.level-1 {
  font-size: 13px;
  color: var(--text-secondary);
}

.chapter-item.level-2 {
  font-size: 12px;
  color: var(--text-secondary);
}

.chapter-item:hover {
  background: var(--hover-bg);
}

.chapter-item.active {
  background: var(--primary-color);
  color: white;
}

.expand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.expand-icon .el-icon {
  transition: transform 0.2s;
  font-size: 12px;
}

.expand-icon .el-icon.expanded {
  transform: rotate(90deg);
}

.expand-placeholder {
  width: 20px;
  flex-shrink: 0;
}

.chapter-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
}

.reader-main {
  flex: 1;
  margin-left: 300px;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  transition: margin-left 0.3s;
}

.chapter-sidebar.collapsed + .reader-main {
  margin-left: 60px;
}

.toolbar {
  position: sticky;
  top: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border-color);
  z-index: 50;
}

.dark-mode .toolbar {
  background: rgba(22, 33, 62, 0.95);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.book-title {
  font-size: 16px;
  font-weight: 500;
  color: var(--text-primary);
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-right .el-button.active {
  background: var(--primary-color);
  color: white;
}

.reading-progress {
  padding: 12px 24px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: var(--border-color);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--primary-color);
  transition: width 0.3s;
}

.progress-text {
  font-size: 14px;
  color: var(--text-secondary);
}

.content-area {
  flex: 1;
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 60px;
}

.chapter-title {
  font-size: 1.8em;
  font-weight: 700;
  text-align: center;
  margin-bottom: 40px;
  color: var(--text-primary);
}

.paragraph {
  margin-bottom: 1.5em;
  text-align: justify;
  color: var(--text-primary);
  text-indent: 2em;
}

.paragraph.footnote {
  font-size: 0.85em;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  padding: 8px 12px;
  border-radius: 4px;
  border-left: 3px solid var(--primary-color);
  text-indent: 0;
}

.highlight-para {
  background: yellow;
  padding: 4px 8px;
  border-radius: 4px;
  animation: highlight-fade 3s ease-in-out;
}

@keyframes highlight-fade {
  0%, 100% {
    background: yellow;
  }
  50% {
    background: transparent;
  }
}

.paragraph :deep(strong) {
  font-weight: bold;
}

.paragraph :deep(em) {
  font-style: italic;
}

.paragraph :deep(.footnote-ref) {
  color: var(--primary-color);
  cursor: pointer;
  font-size: 0.75em;
  vertical-align: super;
  text-decoration: none;
  margin: 0 2px;
}

.paragraph :deep(.footnote-ref:hover) {
  text-decoration: underline;
}

.paragraph :deep(.sup-text) {
  vertical-align: super;
  font-size: 0.75em;
}

.paragraph :deep(sub) {
  vertical-align: sub;
  font-size: 0.75em;
}

.footnotes-section {
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.footnotes-title {
  font-size: 1.1em;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--text-primary);
}

.footnotes-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.footnote-item {
  display: flex;
  gap: 8px;
  font-size: 0.9em;
  color: var(--text-secondary);
  line-height: 1.6;
}

.footnote-number {
  color: var(--primary-color);
  font-weight: 500;
  flex-shrink: 0;
}

.footnote-text {
  flex: 1;
}

.image-container {
  display: flex;
  justify-content: center;
  margin: 24px 0;
}

.image-container.full-width {
  width: 100%;
}

.content-image {
  max-width: 80%;
  border-radius: 8px;
  cursor: pointer;
}

.content-table {
  width: 100%;
  border-collapse: collapse;
  margin: 24px 0;
  font-size: 0.95em;
}

.content-table th,
.content-table td {
  border: 1px solid var(--border-color);
  padding: 10px 14px;
  text-align: left;
}

.content-table th {
  background: var(--bg-secondary);
  font-weight: 600;
}

.content-table tr:nth-child(even) {
  background: var(--bg-secondary);
}

.content-table tr:hover {
  background: var(--hover-bg);
}

.bottom-nav {
  padding: 24px;
  display: flex;
  justify-content: center;
  gap: 24px;
  border-top: 1px solid var(--border-color);
  background: var(--card-bg);
}

.side-arrow {
  position: fixed;
  top: 50%;
  transform: translateY(-50%);
  width: 50px;
  height: 70px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(64, 64, 64, 0.6);
  color: white;
  font-size: 28px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.3s;
  z-index: 100;
  border-radius: 8px;
}

.side-arrow:hover {
  background: rgba(64, 64, 64, 0.9);
}

.side-arrow.visible {
  opacity: 1;
}

.ai-summary-panel {
  position: fixed;
  right: 0;
  top: 60px;
  bottom: 0;
  width: 350px;
  background: var(--card-bg);
  box-shadow: -2px 0 12px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  z-index: 200;
  transition: right 0.3s;
}

.ai-summary-panel.summary-left {
  right: auto;
  left: 300px;
  box-shadow: 2px 0 12px rgba(0, 0, 0, 0.1);
}

.ai-summary-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ai-summary-header h3 {
  margin: 0;
  font-size: 18px;
}

.ai-summary-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.summary-text {
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-primary);
}

.markdown-body {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-primary);
}

.markdown-body h1 {
  font-size: 20px;
  margin: 16px 0 12px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 8px;
}

.markdown-body h2 {
  font-size: 18px;
  margin: 14px 0 10px;
  border-bottom: 1px solid var(--border-color);
  padding-bottom: 6px;
}

.markdown-body h3 {
  font-size: 16px;
  margin: 12px 0 8px;
}

.markdown-body h4, .markdown-body h5, .markdown-body h6 {
  font-size: 15px;
  margin: 10px 0 6px;
}

.markdown-body p {
  margin: 8px 0;
}

.markdown-body ul, .markdown-body ol {
  margin: 8px 0;
  padding-left: 24px;
}

.markdown-body li {
  margin: 4px 0;
}

.markdown-body strong {
  font-weight: 600;
  color: var(--text-primary);
}

.markdown-body em {
  font-style: italic;
}

.markdown-body code {
  background: var(--hover-bg);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: Consolas, Monaco, 'Courier New', monospace;
  font-size: 13px;
}

.markdown-body pre {
  background: var(--hover-bg);
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
}

.markdown-body pre code {
  background: none;
  padding: 0;
}

.markdown-body blockquote {
  border-left: 4px solid var(--primary-color);
  margin: 12px 0;
  padding: 8px 16px;
  background: var(--hover-bg);
  border-radius: 0 8px 8px 0;
}

.markdown-body table {
  border-collapse: collapse;
  margin: 12px 0;
  width: 100%;
}

.markdown-body th, .markdown-body td {
  border: 1px solid var(--border-color);
  padding: 8px 12px;
  text-align: left;
}

.markdown-body th {
  background: var(--hover-bg);
  font-weight: 600;
}

.markdown-body hr {
  border: none;
  border-top: 1px solid var(--border-color);
  margin: 16px 0;
}

.no-summary {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
  color: var(--text-secondary);
}

.content-area.with-summary {
  margin-right: 350px;
}

.content-area.with-summary.summary-left {
  margin-right: 0;
  margin-left: 350px;
}

@media (max-width: 1200px) {
  .chapter-sidebar {
    width: 260px;
  }
  
  .reader-main {
    margin-left: 260px;
  }
}
</style>
