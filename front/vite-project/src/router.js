import { createRouter, createWebHistory } from 'vue-router'

const routes = [
   /* 重定向到realTimePremium，应该是 路由显示/ 而不是 /realTimePremium */
  { path: '/', component: () => import('./components/RealTimePremium.vue') },
  { path: '/realTimePremium', component: () => import('./components/RealTimePremium.vue') },
  { path: '/history', component: () => import('./components/HistoryDetail.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
