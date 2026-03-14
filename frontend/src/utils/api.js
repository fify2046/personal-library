import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 30000,
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
  }
}
