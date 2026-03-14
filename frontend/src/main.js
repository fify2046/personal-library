import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import BookList from './pages/BookList.vue'
import Reader from './pages/Reader.vue'
import BookDetail from './pages/BookDetail.vue'
import ReadingList from './pages/ReadingList.vue'
import Manage from './pages/Manage.vue'
import History from './pages/History.vue'

const routes = [
  { path: '/', name: 'BookList', component: BookList },
  { path: '/book/:id', name: 'BookDetail', component: BookDetail },
  { path: '/read/:bookId/:chapterId?', name: 'Reader', component: Reader },
  { path: '/reading', name: 'ReadingList', component: ReadingList },
  { path: '/manage', name: 'Manage', component: Manage },
  { path: '/history', name: 'History', component: History }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

const app = createApp(App)
app.use(router)
app.use(ElementPlus)
app.mount('#app')
