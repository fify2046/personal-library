import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 7200000,
  headers: {
    'Content-Type': 'application/json'
  }
})

apiClient.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default {
  getBooks(params) {
    return apiClient.get('/books', { params })
  },
  
  getBook(bookId) {
    return apiClient.get(`/books/${bookId}`)
  },
  
  getChapters(bookId) {
    return apiClient.get(`/books/${bookId}/chapters`)
  },
  
  getChapterContent(chapterId) {
    return apiClient.get(`/chapters/${chapterId}/content`)
  },
  
  saveReadingProgress(data) {
    return apiClient.post('/reading/progress', data)
  },
  
  getReadingProgress(bookId) {
    return apiClient.get(`/reading/progress/${bookId}`)
  },
  
  getReadingHistory(params) {
    return apiClient.get('/reading/history', { params })
  },
  
  clearReadingHistory() {
    return apiClient.delete('/reading/history')
  },
  
  deleteReadingHistory(bookId) {
    return apiClient.delete(`/reading/history/${bookId}`)
  },
  
  addFavorite(bookId) {
    return apiClient.post('/favorites/add', { book_id: bookId })
  },
  
  removeFavorite(bookId) {
    return apiClient.post('/favorites/remove', { book_id: bookId })
  },
  
  getFavorites() {
    return apiClient.get('/favorites/list')
  },
  
  checkFavorite(bookId) {
    return apiClient.get(`/favorites/check/${bookId}`)
  },
  
  addToReadingList(bookId) {
    return apiClient.post('/reading_list/add', { book_id: bookId })
  },
  
  removeFromReadingList(bookId) {
    return apiClient.post('/reading_list/remove', { book_id: bookId })
  },
  
  getReadingList() {
    return apiClient.get('/reading_list/list')
  },
  
  checkInReadingList(bookId) {
    return apiClient.get(`/reading_list/check/${bookId}`)
  },
  
  getDisplayMode(bookId) {
    return apiClient.get(`/books/${bookId}/display_mode`)
  },
  
  setDisplayMode(bookId, mode) {
    return apiClient.put(`/books/${bookId}/display_mode`, { display_mode: mode })
  },
  
  deleteBook(bookId) {
    return apiClient.delete(`/books/${bookId}`)
  },
  
  updateBook(bookId, data) {
    return apiClient.put(`/books/${bookId}`, data)
  },
  
  setBookRating(bookId, rating) {
    return apiClient.put(`/books/${bookId}/rating`, { rating })
  },
  
  searchBooks(keyword, page = 1, size = 20) {
    return apiClient.get('/books/search', { params: { keyword, page, size } })
  },

  getSystemConfig() {
    return apiClient.get('/config')
  },

  updateAIModel(data) {
    return apiClient.post('/config/models', data)
  },

  deleteAIModel(modelName) {
    return apiClient.delete(`/config/models/${modelName}`)
  },

  setAIModelEnabled(enabled) {
    return apiClient.put('/config/ai-enabled', null, { params: { enabled } })
  },

  setDefaultModel(modelName) {
    return apiClient.put('/config/default-model', null, { params: { model_name: modelName } })
  },

  updatePrompt(data) {
    return apiClient.put('/config/prompts', data)
  },

  getMinContentLength() {
    return apiClient.get('/config/min-content-length')
  },

  setMinContentLength(length) {
    return apiClient.put('/config/min-content-length', null, { params: { length } })
  },

  getAIStatus() {
    return apiClient.get('/ai/status')
  },

  getChapterSummary(chapterId) {
    return apiClient.get(`/ai/summary/${chapterId}`)
  },

  generateSummary(chapterIds, modelName = null, timeout = 600000, templateName = null) {
    return apiClient.post('/ai/summary/generate',
      { chapter_ids: chapterIds, model_name: modelName, template_name: templateName },
      { timeout }
    )
  },

  deleteSummary(chapterId) {
    return apiClient.delete(`/ai/summary/${chapterId}`)
  },

  getPromptTemplates() {
    return apiClient.get('/config/prompt-templates')
  },

  addPromptTemplate(data) {
    return apiClient.post('/config/prompt-templates', data)
  },

  updatePromptTemplate(templateName, data) {
    return apiClient.put(`/config/prompt-templates/${encodeURIComponent(templateName)}`, data)
  },

  deletePromptTemplate(templateName) {
    return apiClient.delete(`/config/prompt-templates/${encodeURIComponent(templateName)}`)
  },

  getModelRateLimit(modelName) {
    return apiClient.get(`/config/models/${encodeURIComponent(modelName)}/rate-limit`)
  },

  setModelRateLimit(modelName, rateLimit) {
    return apiClient.put(`/config/models/${encodeURIComponent(modelName)}/rate-limit`, null, { params: { rate_limit: rateLimit } })
  },

  getLocalAISettings() {
    const settings = localStorage.getItem('ai_settings')
    return settings ? JSON.parse(settings) : { templateName: null, summaryPosition: 'right' }
  },

  setLocalAISettings(settings) {
    localStorage.setItem('ai_settings', JSON.stringify(settings))
  }
}
