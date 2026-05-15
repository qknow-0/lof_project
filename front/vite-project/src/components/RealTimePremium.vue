<template>
  <div class="lof-app">
    <div class="header">
      <div class="title">
        <h2>LOF 基金实时溢价监控</h2>
        <span class="update-time">数据更新时间：{{ lastUpdateTime }}</span>
      </div>
      <div class="tool-bar">
        <el-button @click="manualRefresh" :loading="loading" type="primary" :icon="Refresh">
          手动刷新
        </el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-input v-model="searchCode" placeholder="基金代码" clearable style="width: 160px;" />
      <el-input v-model="searchName" placeholder="基金名称" clearable style="width: 200px;" />
      <el-select v-model="filterStatus" placeholder="申购状态" clearable style="width: 140px;">
        <el-option v-for="s in statusOptions" :key="s" :label="s" :value="s" />
      </el-select>
      <el-radio-group v-model="showOnlyFavorites" size="small">
        <el-radio-button :label="false">全部基金</el-radio-button>
        <el-radio-button :label="true">我的关注</el-radio-button>
      </el-radio-group>
      <el-button @click="resetFilter" :icon="RefreshRight">重置</el-button>
    </div>

    <el-table :data="displayList" v-loading="loading" height="900" border :default-sort="{ prop: 'premiumRate', order: 'descending' }" style="width: 100%">
      <el-table-column prop="fundCode" label="基金代码" align="center" min-width="100">
        <template #default="{ row }">
          <a class="fund-code-link" @click="goHistory(row)">{{ row.fundCode }}</a>
        </template>
      </el-table-column>
      <el-table-column prop="fundName" label="基金名称" align="center" min-width="130" />
      <el-table-column prop="tradePrice" label="场内价格" align="center" min-width="110" sortable :sort-method="(a, b) => numericSort(a, b, 'tradePrice')" />
      <el-table-column prop="netValue" label="场外净值(昨日)" align="center" min-width="140" sortable :sort-method="(a, b) => numericSort(a, b, 'netValue')" />
      <el-table-column prop="estimateValue" label="估算净值(实时)" align="center" min-width="140" sortable :sort-method="(a, b) => numericSort(a, b, 'estimateValue')" />
      <el-table-column prop="increaseRate" label="涨跌幅" align="center" min-width="110" sortable :sort-method="(a, b) => numericSort(a, b, 'increaseRate')">
        <template #default="{ row }">
          <span :class="getRateClass(row.increaseRate)">
            {{ row.increaseRate }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="premiumRate" label="溢价率(昨日)" align="center" min-width="130" sortable :sort-method="(a, b) => numericSort(a, b, 'premiumRate')">
        <template #default="{ row }">
          <span :class="getRateClass(row.premiumRate)">
            {{ row.premiumRate }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="estimatePremiumRate" label="溢价率(实时)" align="center" min-width="130" sortable :sort-method="(a, b) => numericSort(a, b, 'estimatePremiumRate')">
        <template #default="{ row }">
          <span :class="getRateClass(row.estimatePremiumRate)">
            {{ row.estimatePremiumRate }}%
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="purchaseLimit" label="日限额" align="center" min-width="110" sortable :sort-method="(a, b) => numericSort(a, b, 'purchaseLimit')" />
      <el-table-column label="申购状态" align="center" width="120">
        <template #default="{ row }">
          <el-tag :type="row.purchaseStatus === '暂停申购' ? 'danger' : row.purchaseStatus === '开放申购' ? 'success' : 'info'" size="small" style="white-space: nowrap;">
            {{ row.purchaseStatus }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="fundSize" label="基金规模" align="center" min-width="110" sortable :sort-method="(a, b) => numericSort(a, b, 'fundSize')" />
      <el-table-column prop="turnover" label="成交额" align="center" min-width="110" sortable :sort-method="(a, b) => numericSort(a, b, 'turnover')" />
      <el-table-column label="关注" align="center" width="70" fixed="right">
        <template #default="{ row }">
          <el-switch
            :model-value="favorites.has(row.fundCode)"
            @change="(val) => toggleFavorite(row.fundCode, val)"
          />
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { Refresh, RefreshRight } from '@element-plus/icons-vue'

// 后端接口地址
const API_URL = 'http://127.0.0.1:8000/api/lof'

// ========== IndexedDB 收藏 ==========
const DB_NAME = 'lof-monitor'
const DB_VERSION = 1
const STORE_NAME = 'favorites'

function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)
    request.onerror = () => reject(request.error)
    request.onsuccess = () => resolve(request.result)
    request.onupgradeneeded = (event) => {
      const db = event.target.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'fundCode' })
      }
    }
  })
}

async function addFavoriteDB(fundCode) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    const request = store.put({ fundCode, time: Date.now() })
    request.onsuccess = () => resolve()
    request.onerror = () => reject(request.error)
  })
}

async function removeFavoriteDB(fundCode) {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite')
    const store = tx.objectStore(STORE_NAME)
    const request = store.delete(fundCode)
    request.onsuccess = () => resolve()
    request.onerror = () => reject(request.error)
  })
}

async function getAllFavoritesDB() {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly')
    const store = tx.objectStore(STORE_NAME)
    const request = store.getAll()
    request.onsuccess = () => resolve(request.result.map(item => item.fundCode))
    request.onerror = () => reject(request.error)
  })
}
// ========== IndexedDB 结束 ==========

const fundList = ref([])
const loading = ref(false)
const searchCode = ref('')
const searchName = ref('')
const filterStatus = ref('')
const lastUpdateTime = ref('')
const favorites = ref(new Set())
const showOnlyFavorites = ref(false)
const router = useRouter()

function goHistory(row) {
  router.push({ path: '/history', query: { fundCode: row.fundCode, fundName: row.fundName } })
}

function formatTime(date) {
  const pad = n => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

// 申购状态选项
const statusOptions = computed(() => {
  const set = new Set(fundList.value.map(i => i.purchaseStatus).filter(Boolean))
  return Array.from(set).sort()
})

// 筛选
const displayList = computed(() => {
  let list = [...fundList.value]
  if (showOnlyFavorites.value) {
    list = list.filter(i => favorites.value.has(i.fundCode))
  }
  if (searchCode.value) {
    list = list.filter(i => String(i.fundCode).includes(searchCode.value.trim()))
  }
  if (searchName.value) {
    list = list.filter(i => String(i.fundName).includes(searchName.value.trim()))
  }
  if (filterStatus.value) {
    list = list.filter(i => i.purchaseStatus === filterStatus.value)
  }
  return list
})

function resetFilter() {
  searchCode.value = ''
  searchName.value = ''
  filterStatus.value = ''
  showOnlyFavorites.value = false
}

// 获取数据
async function fetchData() {
  if (loading.value) return
  loading.value = true
  try {
    const res = await axios.get(API_URL)
    if (res.data.code === 200) {
      fundList.value = res.data.data
      lastUpdateTime.value = formatTime(new Date())
    } else {
      ElMessage.error(res.data.msg || '数据获取失败')
    }
  } catch (err) {
    ElMessage.error('请求失败：请确认 Python 后端已启动')
  } finally {
    loading.value = false
  }
}

// 手动刷新
function manualRefresh() {
  fetchData()
}

// 数值排序方法（供 el-table 列排序使用）
function numericSort(a, b, prop) {
  const va = parseFloat(a[prop]) || 0
  const vb = parseFloat(b[prop]) || 0
  return va - vb
}

// 颜色样式
function getRateClass(rate) {
  const num = parseFloat(rate) || 0
  if (num > 0) return 'rate-up'
  if (num < 0) return 'rate-down'
  return 'rate-zero'
}

async function loadFavorites() {
  try {
    const codes = await getAllFavoritesDB()
    favorites.value = new Set(codes)
  } catch (e) {
    console.error('加载收藏失败', e)
  }
}

async function toggleFavorite(fundCode, isChecked) {
  try {
    if (isChecked) {
      await addFavoriteDB(fundCode)
      favorites.value.add(fundCode)
    } else {
      await removeFavoriteDB(fundCode)
      favorites.value.delete(fundCode)
    }
  } catch (e) {
    console.error('收藏操作失败', e)
    ElMessage.error('收藏操作失败')
  }
}

onMounted(() => {
  loadFavorites()
  fetchData()
})
</script>

<style scoped>
.lof-app {
  padding: 24px;
  box-sizing: border-box;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
  overflow-x: auto;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.title {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.update-time {
  font-size: 13px;
  color: #999;
  text-align: left;
}
.tool-bar {
  display: flex;
  gap: 12px;
}
button {
  padding: 4px 10px;
  cursor: pointer;
  border-radius: 4px;
  border: 1px solid #ccc;
}
.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  align-items: center;
}
.rate-up {
  color: #f53f3f;
  font-weight: bold;
}
.rate-down {
  color: #009944;
  font-weight: bold;
}
.rate-zero {
  color: #666;
}
.fund-code-link {
  color: #409eff;
  cursor: pointer;
  /* text-decoration: none; */
  text-decoration: underline;
}

</style>