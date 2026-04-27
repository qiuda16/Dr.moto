<template>
  <div class="dashboard">
    <section class="hero card">
      <div class="hero-main">
        <div class="hero-eyebrow">{{ heroEyebrow }}</div>
        <div class="hero-title">{{ heroTitle }}</div>
        <div class="hero-copy">
          {{ heroCopy }}
        </div>
        <div class="hero-actions">
          <el-button type="primary" @click="goQuickIntake">快速接车</el-button>
          <el-button @click="jumpToOrders('in_progress')">看施工中</el-button>
          <el-button @click="goCreateCustomer">新建客户</el-button>
        </div>
      </div>

      <div class="hero-side">
        <div class="hero-money-label">今日营业额</div>
        <div class="hero-money">¥{{ currency(overview.kpi.today_paid_amount) }}</div>
        <div class="hero-status">
          <span class="hero-chip">待交付 {{ statusCount('ready') }}</span>
          <span class="hero-chip">待施工 {{ statusCount('quoted') }}</span>
          <span class="hero-chip">加急 {{ overview.kpi.urgent_orders_count || 0 }}</span>
          <span class="hero-chip danger">超期 {{ overview.kpi.overdue_active_count }}</span>
        </div>
      </div>
    </section>

    <section class="metric-grid">
      <button class="metric-card card" @click="jumpToOrders()">
        <span>工单总数</span>
        <strong>{{ overview.orders.total }}</strong>
        <small>查看全部工单</small>
      </button>
      <button class="metric-card card" @click="jumpToOrders('in_progress')">
        <span>施工中</span>
        <strong>{{ statusCount('in_progress') }}</strong>
        <small>当前正在施工的车辆</small>
      </button>
      <button class="metric-card card" @click="jumpToOrders('ready')">
        <span>待交付</span>
        <strong>{{ statusCount('ready') }}</strong>
        <small>已经可以交车的工单</small>
      </button>
      <button class="metric-card card" @click="jumpToOrders('done')">
        <span>已完成</span>
        <strong>{{ overview.orders.done }}</strong>
        <small>历史完工归档</small>
      </button>
    </section>

    <section class="focus-grid">
      <div class="card focus-card">
        <div class="section-title">今日重点待办</div>
        <div class="focus-list">
          <button class="focus-item" @click="jumpToOrders('quoted')">
            <div>
              <strong>待施工</strong>
              <span>报价确认后等待开工安排</span>
            </div>
            <b>{{ statusCount('quoted') }}</b>
          </button>
          <button class="focus-item" @click="jumpToOrders('in_progress')">
            <div>
              <strong>施工中</strong>
              <span>继续补齐过程记录和完工体检</span>
            </div>
            <b>{{ statusCount('in_progress') }}</b>
          </button>
          <button class="focus-item" @click="jumpToOrders('ready')">
            <div>
              <strong>待交付</strong>
              <span>先确认交车说明，再统一出单</span>
            </div>
            <b>{{ statusCount('ready') }}</b>
          </button>
          <button class="focus-item" @click="jumpToOrders('draft')">
            <div>
              <strong>草稿待接车</strong>
              <span>补齐接车信息，避免记录悬空</span>
            </div>
            <b>{{ statusCount('draft') }}</b>
          </button>
        </div>
      </div>

      <div class="card focus-card">
        <div class="section-title">经营提醒</div>
        <div class="summary-list">
          <div class="summary-item">
            <span>待收款单数</span>
            <strong>{{ overview.payments.pending_count }}</strong>
          </div>
          <div class="summary-item">
            <span>有效报价数</span>
            <strong>{{ overview.quotes.active_count }}</strong>
          </div>
          <div class="summary-item">
            <span>今日完工</span>
            <strong>{{ overview.kpi.today_done_orders }}</strong>
          </div>
          <div class="summary-item danger">
            <span>超期未完工</span>
            <strong>{{ overview.kpi.overdue_active_count }}</strong>
          </div>
          <div class="summary-item warn">
            <span>加急工单</span>
            <strong>{{ overview.kpi.urgent_orders_count || 0 }}</strong>
          </div>
          <div class="summary-item warn">
            <span>返修工单</span>
            <strong>{{ overview.kpi.rework_orders_count || 0 }}</strong>
          </div>
          <div class="summary-item">
            <span>待客户确认报价</span>
            <strong>{{ overview.kpi.quote_pending_confirmation_count || 0 }}</strong>
          </div>
          <div class="summary-item">
            <span>即将到时交车</span>
            <strong>{{ overview.kpi.promised_due_soon_count || 0 }}</strong>
          </div>
          <div class="summary-item">
            <span>工位占用</span>
            <strong>{{ overview.kpi.service_bay_active_count || 0 }}</strong>
          </div>
          <div class="summary-item">
            <span>客单均值</span>
            <strong>¥{{ currency(overview.kpi.avg_ticket_amount) }}</strong>
          </div>
        </div>

        <div class="status-panel">
          <div class="status-panel-title">状态分布</div>
          <div class="status-wrap">
            <el-tag
              v-for="item in statusList"
              :key="item.status"
              :type="statusTagType(item.status)"
              size="large"
              effect="plain"
            >
              {{ statusLabel(item.status) }} {{ item.count }}
            </el-tag>
          </div>
        </div>
      </div>
    </section>

    <section class="ops-grid">
      <div class="card ops-card">
        <div class="section-title">车间负载</div>
        <div class="section-subtitle">{{ workshopSubtitle }}</div>
        <div class="resource-board">
          <div class="resource-board-block">
            <div class="resource-board-title">技师负载</div>
            <div v-if="overview.operations.technicians.length" class="resource-list">
              <div v-for="item in overview.operations.technicians" :key="item.name" class="resource-item">
                <strong>{{ item.name }}</strong>
                <span>{{ item.active_count }} 单</span>
              </div>
            </div>
            <div v-else class="muted-inline">暂无已分配技师的在场工单</div>
          </div>

          <div class="resource-board-block">
            <div class="resource-board-title">工位占用</div>
            <div v-if="overview.operations.service_bays.length" class="resource-list">
              <div v-for="item in overview.operations.service_bays" :key="item.name" class="resource-item">
                <strong>{{ item.name }}</strong>
                <span>{{ item.active_count }} 台车</span>
              </div>
            </div>
            <div v-else class="muted-inline">暂无工位占用数据</div>
          </div>
        </div>
      </div>

      <div class="card ops-card ai-card">
        <div class="section-title">AI 助手</div>
        <div class="section-subtitle">{{ assistantSubtitle }}</div>
        <el-input
          v-model="assistantPrompt"
          type="textarea"
          :rows="3"
          :placeholder="assistantPlaceholder"
          @keydown.ctrl.enter.prevent="askAssistant"
        />
        <div class="assistant-actions">
          <div class="assistant-suggestions">
            <button
              v-for="item in promptSuggestions"
              :key="item"
              type="button"
              class="assistant-chip"
              @click="usePrompt(item)"
            >
              {{ item }}
            </button>
          </div>
          <el-button type="primary" :loading="assistantLoading" @click="askAssistant">询问 AI</el-button>
        </div>

        <div v-if="assistantReply" class="assistant-result">
          <div class="assistant-result-head">
            <div>
              <strong>AI 回答</strong>
              <div class="assistant-result-subtitle">先给结论，再给建议动作和参考来源。</div>
            </div>
            <div class="assistant-inline-actions">
              <el-button text @click="retryAssistant">重试</el-button>
              <el-button text @click="copyAssistantAnswer">复制</el-button>
            </div>
          </div>
          <div v-if="assistantReply.meta?.length" class="assistant-meta">
            <span
              v-for="(item, index) in assistantReply.meta"
              :key="`${item.label}-${index}`"
              :class="['assistant-meta-chip', `assistant-meta-chip-${item.tone || 'muted'}`]"
            >
              {{ item.label }}
            </span>
          </div>
          <div class="assistant-result-body">{{ assistantReply.response }}</div>
          <div v-if="assistantReply.action_cards?.length" class="assistant-action-list">
            <div v-for="(item, index) in assistantReply.action_cards" :key="`${item.action}-${index}`" class="assistant-action-card">
              <strong>{{ item.label || '建议动作' }}</strong>
              <span>{{ item.description || item.action }}</span>
            </div>
          </div>
          <div v-if="assistantReply.sources?.length" class="assistant-source-list">
            <div
              v-for="(item, index) in assistantReply.sources"
              :key="`${item.type || 'source'}-${index}`"
              class="assistant-source-item"
            >
              <strong>{{ item.label || sourceTypeLabel(item.type) }}</strong>
              <span>{{ item.summary || sourceTypeLabel(item.type) }}</span>
            </div>
          </div>
          <div v-if="assistantReply.suggested_actions?.length" class="assistant-result-tags">
            <button
              v-for="(item, index) in assistantReply.suggested_actions"
              :key="`${item}-${index}`"
              type="button"
              @click="runActionSuggestion(item)"
            >
              {{ item }}
            </button>
          </div>
        </div>

        <div v-else-if="assistantLoading" class="assistant-empty assistant-empty-pending">
          <strong>AI 正在整理上下文</strong>
          <span>会先看门店总览，再结合你当前的问题给结论。</span>
        </div>

        <div v-else class="assistant-empty">
          <strong>这里会显示 AI 回答</strong>
          <span>适合快速问运营重点、工单优先级、待交付风险，或者某张单下一步该怎么做。</span>
        </div>
      </div>

      <div class="card ops-card">
        <div class="section-title">建议先做的事</div>
        <div class="ops-list">
          <button class="ops-item" @click="jumpToOrders('ready')">
            <strong>先处理待交付</strong>
            <span>对客户体感最强，优先减少压单</span>
          </button>
          <button class="ops-item" @click="jumpToOrders('quoted')">
            <strong>再处理待施工</strong>
            <span>避免车辆久等，尽快安排工位和技师</span>
          </button>
          <button class="ops-item" @click="jumpToOrders('draft')">
            <strong>最后清理草稿</strong>
            <span>避免前台接车信息长期悬空</span>
          </button>
        </div>
      </div>
    </section>

    <section class="card recent-section">
      <div class="recent-head">
        <div>
          <div class="section-title">最近工单</div>
          <div class="section-subtitle">方便快速回看最新进店车辆和处理状态。</div>
        </div>
        <div class="recent-actions">
          <el-button @click="jumpToOrders('ready')">看待交付</el-button>
          <el-button @click="jumpToOrders('quoted')">看待施工</el-button>
          <el-button type="primary" plain @click="jumpToOrders()">进入工单中心</el-button>
        </div>
      </div>

      <el-table
        :data="overview.recent.orders"
        v-loading="loading"
        :element-loading-text="TABLE_LOADING_TEXT"
        :empty-text="EMPTY_TEXT.recentOrders"
        style="width: 100%"
      >
        <el-table-column prop="id" label="工单号" min-width="240" />
        <el-table-column prop="vehicle_plate" label="车牌" width="140" />
        <el-table-column label="提醒" width="180">
          <template #default="scope">
            <div class="inline-tags">
              <span v-if="scope.row.is_urgent" class="inline-tag danger">加急</span>
              <span v-if="scope.row.is_rework" class="inline-tag warn">返修</span>
              <span v-if="scope.row.assigned_technician">{{ scope.row.assigned_technician }}</span>
              <span v-if="!scope.row.is_urgent && !scope.row.is_rework && !scope.row.assigned_technician" class="muted-inline">暂无</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="130">
          <template #default="scope">
            <el-tag :type="statusTagType(scope.row.status)">{{ statusLabel(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="customer_id" label="客户ID" width="120" />
        <el-table-column prop="description" label="客户主诉" min-width="220" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="220" />
      </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import request from '../utils/request'
import { applyAppSettings, createAppSettingsState } from '../composables/appSettings'
import { EMPTY_TEXT, TABLE_LOADING_TEXT } from '../constants/uiState'

const router = useRouter()
const loading = ref(false)
const assistantLoading = ref(false)
const appSettings = reactive(createAppSettingsState())
const assistantPrompt = ref('')
const assistantReply = ref(null)

const overview = reactive({
  orders: { total: 0, active: 0, done: 0, status_counts: {} },
  payments: { pending_count: 0, paid_amount_total: 0 },
  quotes: { active_count: 0 },
  kpi: {
    today_new_orders: 0,
    today_done_orders: 0,
    today_paid_amount: 0,
    overdue_active_count: 0,
    urgent_orders_count: 0,
    rework_orders_count: 0,
    quote_pending_confirmation_count: 0,
    promised_due_soon_count: 0,
    service_bay_active_count: 0,
    avg_ticket_amount: 0,
  },
  recent: { orders: [] },
  operations: { technicians: [], service_bays: [] },
})

const statusList = computed(() =>
  Object.entries(overview.orders.status_counts || {})
    .map(([status, count]) => ({ status, count }))
    .sort((a, b) => b.count - a.count),
)

const focusCount = computed(() =>
  statusCount('quoted') +
  statusCount('in_progress') +
  statusCount('ready') +
  Number(overview.kpi.overdue_active_count || 0),
)

const normalizedStoreName = computed(() => String(appSettings.store_name || '').trim() || '机车博士')
const heroEyebrow = computed(() => `${normalizedStoreName.value} · 今日门店总览`)
const heroTitle = computed(() => `先看清 ${normalizedStoreName.value} 今天要处理什么，再进入具体工单`)
const heroCopy = computed(
  () =>
    `今天新建工单 ${overview.kpi.today_new_orders} 单，已完成 ${overview.kpi.today_done_orders} 单，当前需要优先关注的在场车辆共有 ${focusCount.value} 项。`,
)
const workshopSubtitle = computed(
  () => `先看 ${normalizedStoreName.value} 当前技师和工位有没有压单，再决定今天怎么排施工和交付。`,
)
const assistantSubtitle = computed(
  () => `快速问 ${normalizedStoreName.value} 今天该盯什么、哪台车最紧急，或者某张工单下一步该做什么。`,
)
const assistantPlaceholder = computed(
  () => `例如：${normalizedStoreName.value} 今天哪些工单最该优先跟进？`,
)

const promptSuggestions = computed(() => {
  const suggestions = [
    '今天先盯什么？',
    '待交付工单怎么排优先级？',
    '哪些报价还没确认？',
  ]
  if (Number(overview.kpi.overdue_active_count || 0) > 0) suggestions.unshift('超期工单里哪些最该先处理？')
  if (Number(overview.kpi.urgent_orders_count || 0) > 0) suggestions.unshift('加急工单怎么安排最稳？')
  return suggestions.slice(0, 4)
})

function sourceTypeLabel(type) {
  const map = {
    customer: '客户档案',
    vehicle: '车辆档案',
    work_order: '当前工单',
    health_record: '最近体检',
    recent_work_order: '相关工单',
    knowledge: '知识库',
    knowledge_document: '标准资料',
    vehicle_catalog_model: '车型目录',
  }
  return map[type] || '参考来源'
}

function buildAssistantMeta(data) {
  const debug = data?.debug || {}
  const items = []

  if (debug.write_executed) items.push({ tone: 'success', label: `已执行 ${debug.write_action || '动作'}` })
  else if (debug.write_intent_detected) items.push({ tone: 'warn', label: `待补全 ${debug.write_action || '动作'}` })
  else if (debug.knowledge_gap_fast_path) items.push({ tone: 'warn', label: '资料不足' })
  else if (debug.global_query_fast_path) items.push({ tone: 'info', label: '全局查询' })
  else if (debug.entity_intent_fast_path || debug.fact_guard_triggered) items.push({ tone: 'info', label: '业务快答' })

  if (debug.model) items.push({ tone: 'muted', label: debug.model })
  if (debug.primary_domain) items.push({ tone: 'muted', label: `域 ${debug.primary_domain}` })
  return items
}

function currency(value) {
  return Number(value || 0).toLocaleString('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })
}

function statusCount(status) {
  return Number(overview.orders.status_counts?.[status] || 0)
}

function statusLabel(status) {
  const map = {
    draft: '草稿',
    confirmed: '已接车',
    quoted: '待施工',
    in_progress: '施工中',
    ready: '待交付',
    done: '已完成',
    cancel: '已取消',
  }
  return map[status] || status || '未知'
}

function statusTagType(status) {
  const map = {
    draft: 'info',
    confirmed: 'warning',
    quoted: 'warning',
    in_progress: 'primary',
    ready: 'success',
    done: '',
    cancel: 'danger',
  }
  return map[status] || 'info'
}

function resetAssistantPrompt() {
  assistantPrompt.value = `帮我总结${normalizedStoreName.value}今天最需要优先跟进的事项，并建议下一步。`
}

async function loadAppSettings() {
  try {
    const data = await request.get('/mp/settings')
    applyAppSettings(appSettings, data)
  } catch {
    applyAppSettings(appSettings)
  } finally {
    resetAssistantPrompt()
  }
}

async function loadOverview() {
  loading.value = true
  try {
    const data = await request.get('/mp/dashboard/overview')
    Object.assign(overview.orders, data?.orders || {})
    Object.assign(overview.payments, data?.payments || {})
    Object.assign(overview.quotes, data?.quotes || {})
    Object.assign(overview.kpi, data?.kpi || {})
    overview.recent.orders = data?.recent?.orders || []
    overview.operations.technicians = data?.operations?.technicians || []
    overview.operations.service_bays = data?.operations?.service_bays || []
  } catch (error) {
    ElMessage.error(error?.message || '加载总览失败')
  } finally {
    loading.value = false
  }
}

async function askAssistant() {
  const message = String(assistantPrompt.value || '').trim()
  if (!message) {
    ElMessage.warning('请先输入问题')
    return
  }

  assistantLoading.value = true
  try {
    const data = await request.post('/ai/assistant/chat', {
      message,
      context: {
        store_overview: overview,
      },
    })
    assistantReply.value = {
      response: data?.response || 'AI 暂时没有返回内容。',
      suggested_actions: data?.suggested_actions || [],
      action_cards: data?.action_cards || [],
      sources: data?.sources || [],
      meta: buildAssistantMeta(data),
      prompt: message,
    }
  } catch (error) {
    assistantReply.value = null
    ElMessage.error(error?.message || 'AI 助手暂时不可用')
  } finally {
    assistantLoading.value = false
  }
}

function usePrompt(prompt) {
  assistantPrompt.value = prompt
  askAssistant()
}

function runActionSuggestion(prompt) {
  assistantPrompt.value = prompt
  askAssistant()
}

function retryAssistant() {
  if (!assistantReply.value?.prompt) return
  assistantPrompt.value = assistantReply.value.prompt
  askAssistant()
}

async function copyAssistantAnswer() {
  if (!assistantReply.value?.response) return
  try {
    await navigator.clipboard.writeText(assistantReply.value.response)
    ElMessage.success('已复制')
  } catch {
    ElMessage.warning('复制失败，请手动复制')
  }
}

function jumpToOrders(status) {
  if (status) {
    router.push({ name: 'orders', query: { status } })
    return
  }
  router.push({ name: 'orders' })
}

function goQuickIntake() {
  router.push({ name: 'orders', query: { quick_intake: '1' } })
}

function goCreateCustomer() {
  router.push({ name: 'customers', query: { create: '1' } })
}

function handleStoreChanged() {
  loadAppSettings()
}

onMounted(() => {
  loadAppSettings()
  loadOverview()
  window.addEventListener('drmoto-store-changed', handleStoreChanged)
})

onBeforeUnmount(() => {
  window.removeEventListener('drmoto-store-changed', handleStoreChanged)
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
  padding: 20px;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) minmax(260px, 0.9fr);
  gap: 20px;
  align-items: stretch;
}

.hero-eyebrow {
  color: #0f6cbd;
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 8px;
}

.hero-title {
  font-size: 28px;
  line-height: 1.25;
  font-weight: 700;
  color: #0f172a;
}

.hero-copy {
  margin-top: 12px;
  color: #475569;
  line-height: 1.75;
}

.hero-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  flex-wrap: wrap;
}

.hero-side {
  border-radius: 14px;
  background: linear-gradient(145deg, #0f6cbd, #2d9cdb);
  color: #fff;
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.hero-money-label {
  font-size: 13px;
  opacity: 0.88;
}

.hero-money {
  margin-top: 10px;
  font-size: 34px;
  font-weight: 700;
}

.hero-status {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 20px;
}

.hero-chip {
  background: rgba(255, 255, 255, 0.14);
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
}

.hero-chip.danger {
  background: rgba(220, 38, 38, 0.22);
}

.metric-grid,
.focus-grid,
.ops-grid {
  display: grid;
  gap: 16px;
}

.metric-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.focus-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.ops-grid {
  grid-template-columns: 1fr 1fr 1fr;
}

.metric-card,
.focus-item,
.ops-item,
.secondary-item {
  border: none;
  text-align: left;
  cursor: pointer;
}

.metric-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-card span,
.summary-item span,
.section-subtitle,
.focus-item span,
.ops-item span,
.secondary-item span,
.muted-inline {
  color: #64748b;
}

.metric-card strong {
  font-size: 28px;
  color: #0f172a;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 8px;
}

.section-subtitle {
  font-size: 13px;
  line-height: 1.65;
}

.focus-list,
.ops-list,
.secondary-links,
.resource-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.focus-item,
.ops-item,
.secondary-item,
.resource-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 14px 16px;
  border-radius: 12px;
  background: #f8fafc;
}

.focus-item strong,
.ops-item strong,
.secondary-item strong,
.resource-item strong {
  color: #0f172a;
}

.summary-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  border-radius: 12px;
  background: #f8fafc;
}

.summary-item strong {
  color: #0f172a;
}

.summary-item.danger {
  background: #fff1f2;
}

.summary-item.warn {
  background: #fff7ed;
}

.status-panel {
  margin-top: 14px;
}

.status-panel-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 10px;
}

.status-wrap {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.resource-board {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.resource-board-title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 10px;
}

.assistant-actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-top: 14px;
}

.assistant-suggestions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.assistant-chip {
  border: none;
  border-radius: 999px;
  padding: 6px 10px;
  background: #eff6ff;
  color: #0f6cbd;
  cursor: pointer;
}

.assistant-result,
.assistant-empty {
  margin-top: 14px;
  border-radius: 12px;
  background: #f8fafc;
  padding: 14px;
}

.assistant-empty-pending {
  border: 1px dashed #cfe0f5;
  background: linear-gradient(180deg, #f8fbff 0%, #f2f7fd 100%);
}

.assistant-result-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  gap: 12px;
}

.assistant-result-subtitle {
  color: #64748b;
  font-size: 12px;
  margin-top: 4px;
}

.assistant-inline-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.assistant-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.assistant-meta-chip {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  line-height: 1;
  border: 1px solid transparent;
}

.assistant-meta-chip-success {
  background: #e9f8ef;
  color: #13663a;
  border-color: #bfe4ca;
}

.assistant-meta-chip-warn {
  background: #fff5e8;
  color: #9a5a00;
  border-color: #f1d19b;
}

.assistant-meta-chip-info {
  background: #eef5ff;
  color: #1c5bb8;
  border-color: #c9dcfb;
}

.assistant-meta-chip-muted {
  background: #f3f6f9;
  color: #60758c;
  border-color: #d7e0e8;
}

.assistant-result-body {
  color: #0f172a;
  line-height: 1.75;
  white-space: pre-wrap;
}

.assistant-action-list,
.assistant-source-list {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.assistant-action-card,
.assistant-source-item {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid #dbe7f2;
  border-radius: 10px;
  background: #fff;
}

.assistant-action-card strong,
.assistant-source-item strong {
  color: #0f172a;
}

.assistant-action-card span,
.assistant-source-item span {
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.assistant-result-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.assistant-result-tags button {
  display: inline-flex;
  padding: 5px 10px;
  border-radius: 999px;
  background: #e2e8f0;
  color: #334155;
  font-size: 12px;
  border: none;
  cursor: pointer;
}

.assistant-empty {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.recent-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
}

.recent-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.inline-tags {
  display: flex;
  gap: 6px;
  align-items: center;
  flex-wrap: wrap;
}

.inline-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 42px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: #e2e8f0;
  color: #334155;
}

.inline-tag.warn {
  background: #ffedd5;
  color: #9a3412;
}

.inline-tag.danger {
  background: #fee2e2;
  color: #b91c1c;
}

@media (max-width: 1200px) {
  .metric-grid,
  .focus-grid,
  .ops-grid,
  .hero,
  .resource-board {
    grid-template-columns: 1fr;
  }

  .assistant-actions {
    flex-direction: column;
  }
}
</style>
