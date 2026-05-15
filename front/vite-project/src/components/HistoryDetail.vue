<template>
  <div class="history-app">
    <div class="history-header">
      <div class="header-left">
        <h2>{{ fundName }} ({{ fundCode }}) 历史数据</h2>
      </div>
      <a class="back-link" @click="goBack">&larr; 返回看板</a>
    </div>

    <el-table :data="historyList" v-loading="loading" border height="800" style="width: 100%">
      <el-table-column prop="date" label="价格日期" align="center" min-width="110" />
      <el-table-column prop="price" label="收盘价" align="center" min-width="90" />
      <el-table-column prop="navDate" label="净值日期" align="center" min-width="110" />
      <el-table-column prop="nav" label="净值" align="center" min-width="90" />
      <el-table-column label="溢价率" align="center" min-width="100">
        <template #default="{ row }">
          <span :class="getRateClass(row.premiumRate)">
            {{ formatPremium(row.premiumRate) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="turnover" label="成交额(万元)" align="center" min-width="120" />
      <el-table-column prop="shareVolume" label="场内份额(万份)" align="center" min-width="130" />
      <el-table-column label="场内新增(万份)" align="center" min-width="120">
        <template #default="{ row }">
          <span :class="getRateClass(row.changeAmount)">
            {{ row.changeAmount != null ? formatChange(row.changeAmount) : '-' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="份额涨幅" align="center" min-width="100">
        <template #default="{ row }">
          <span :class="getRateClass(row.changePct)">
            {{ row.changePct != null ? formatPct(row.changePct) : '-' }}
          </span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup name="history">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const API_URL = 'http://127.0.0.1:8000/api/lof/history'

const route = useRoute()
const router = useRouter()

const fundCode = ref(route.query.fundCode || '')
const fundName = ref(route.query.fundName || '')
const historyList = ref([])
const loading = ref(false)

function goBack() {
  router.push('/')
}

async function fetchHistory() {
  if (!fundCode.value) {
    ElMessage.error('缺少基金代码参数')
    return
  }
  loading.value = true
  try {
    const res = await axios.get(API_URL, {
      params: { fund_code: fundCode.value, fund_name: fundName.value }
    })
    if (res.data.code === 200) {
      historyList.value = res.data.data
      fundName.value = res.data.fundName || fundName.value
    } else {
      ElMessage.error(res.data.msg || '获取历史数据失败')
    }
  } catch (err) {
    ElMessage.error('请求失败：请确认 Python 后端已启动')
  } finally {
    loading.value = false
  }
}

function formatPremium(rate) {
  if (rate == null) return '-'
  const num = parseFloat(rate)
  if (isNaN(num)) return '-'
  return (num > 0 ? '+' : '') + num + '%'
}

function formatPct(val) {
  if (val == null) return '-'
  const num = parseFloat(val)
  if (isNaN(num)) return '-'
  return (num > 0 ? '+' : '') + num.toFixed(3) + '%'
}

function formatChange(val) {
  if (val == null) return '-'
  const num = parseFloat(val)
  if (isNaN(num)) return '-'
  return (num > 0 ? '+' : '') + num.toFixed(2)
}

function getRateClass(rate) {
  const num = parseFloat(rate) || 0
  if (num > 0) return 'rate-up'
  if (num < 0) return 'rate-down'
  return 'rate-zero'
}

onMounted(() => {
  fetchHistory()
})
</script>

<style scoped>
.history-app {
  padding: 24px;
  box-sizing: border-box;
  width: 100%;
  max-width: 1600px;
  margin: 0 auto;
}
.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #6A5ACD, #4B0082);
  padding: 16px 24px;
  border-radius: 8px;
  color: #fff;
}
.history-header h2 {
  margin: 0;
  font-size: 20px;
  color: #fff;
}
.back-link {
  color: #ccc;
  cursor: pointer;
  font-size: 14px;
  text-decoration: none;
  transition: color 0.2s;
}
.back-link:hover {
  color: #fff;
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
</style>
