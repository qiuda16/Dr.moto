<template>
  <div class="dashboard">
    <section class="hero card">
      <div class="hero-main">
        <div class="hero-title">{{ heroTitle }}</div>
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

    <button v-if="!assistantOpen" type="button" class="ai-float-trigger" @click="openAssistant">
      <span class="ai-float-trigger-icon">AI</span>
      <span class="ai-float-trigger-text">助手</span>
    </button>

    <transition name="ai-panel-slide">
      <aside v-if="assistantOpen" class="ai-panel">
        <div class="ai-panel-header">
          <div>
            <div class="section-title">AI 助手</div>
            <div class="ai-panel-subtitle">{{ assistantSubtitle }}</div>
          </div>
          <div class="ai-panel-actions">
            <el-button text @click="clearAssistantConversation">清空</el-button>
            <el-button text @click="closeAssistant">关闭</el-button>
          </div>
        </div>

        <div ref="assistantScrollRef" class="ai-panel-history">
          <div
            v-for="message in assistantMessages"
            :key="message.id"
            :class="['ai-message', `ai-message-${message.role}`]"
          >
            <div class="ai-message-bubble">
              <div v-if="message.role === 'assistant' && message.meta?.length" class="assistant-meta">
                <span
                  v-for="(item, index) in message.meta"
                  :key="`${message.id}-${item.label}-${index}`"
                  :class="['assistant-meta-chip', `assistant-meta-chip-${item.tone || 'muted'}`]"
                >
                  {{ item.label }}
                </span>
              </div>

              <div v-if="message.role === 'assistant'" class="assistant-response-stack">
                <div v-if="assistantResponseSummary(message.text).length" class="assistant-summary-card">
                  <div class="assistant-summary-label">结论摘要</div>
                  <div class="assistant-summary-text">{{ assistantResponseSummary(message.text)[0] }}</div>
                </div>

                <div
                  v-for="section in assistantResponseSections(message.text)"
                  :key="`${message.id}-${section.title}`"
                  class="assistant-response-section"
                  :class="[`assistant-response-section-${section.kind}`]"
                >
                  <div class="assistant-response-section-head">
                    <strong>{{ section.title }}</strong>
                    <span v-if="section.kind === 'steps'">建议先按顺序执行</span>
                  </div>

                  <ul v-if="section.kind === 'steps' || section.kind === 'bullets'" class="assistant-response-list">
                    <li v-for="(item, index) in section.items" :key="`${message.id}-${section.title}-${index}`">
                      {{ item }}
                    </li>
                  </ul>

                  <div v-else class="assistant-response-text">
                    <p v-for="(item, index) in section.items" :key="`${message.id}-${section.title}-${index}`">
                      {{ item }}
                    </p>
                  </div>
                </div>
              </div>

              <div v-else class="ai-message-text">{{ message.text }}</div>

              <div v-if="message.action_cards?.length" class="assistant-action-list">
                <div
                  v-for="(item, index) in message.action_cards"
                  :key="`${message.id}-${item.action || 'action'}-${index}`"
                  class="assistant-action-card"
                >
                  <strong>{{ item.label || '建议动作' }}</strong>
                  <span>{{ item.description || item.action }}</span>
                </div>
              </div>

              <div v-if="message.sources?.length" class="assistant-source-list">
                <div
                  v-for="(item, index) in message.sources"
                  :key="`${message.id}-${item.type || 'source'}-${index}`"
                  class="assistant-source-item"
                >
                  <strong>{{ item.label || sourceTypeLabel(item.type) }}</strong>
                  <span>{{ item.summary || sourceTypeLabel(item.type) }}</span>
                </div>
              </div>

              <div v-if="message.suggested_actions?.length" class="assistant-result-tags">
                <button
                  v-for="(item, index) in message.suggested_actions"
                  :key="`${message.id}-${item}-${index}`"
                  type="button"
                  @click="runActionSuggestion(item)"
                >
                  {{ item }}
                </button>
              </div>

              <div v-if="message.role === 'assistant' && message.prompt" class="ai-message-tools">
                <el-button text size="small" @click="retryMessage(message)">重试</el-button>
                <el-button text size="small" @click="copyMessage(message)">复制</el-button>
              </div>
            </div>
          </div>

          <div v-if="assistantLoading" class="ai-message ai-message-assistant">
            <div class="ai-message-bubble ai-message-pending">
              <strong>正在整理上下文</strong>
              <span>会先看门店总览，再结合你当前的问题给结论。</span>
            </div>
          </div>
        </div>

        <div class="ai-panel-composer">
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

          <el-input
            v-model="assistantInput"
            class="ai-composer-input"
            type="textarea"
            :rows="3"
            :placeholder="assistantPlaceholder"
            @keydown.enter.exact.prevent="askAssistant"
          />

          <div class="ai-panel-submit">
            <span class="ai-panel-hint">Enter 发送，Shift + Enter 换行</span>
            <el-button type="primary" :loading="assistantLoading" @click="askAssistant">发送</el-button>
          </div>
        </div>
      </aside>
    </transition>

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
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import request from '../utils/request'
import { getAuthToken } from '../utils/auth'
import { applyAppSettings, createAppSettingsState } from '../composables/appSettings'
import { EMPTY_TEXT, TABLE_LOADING_TEXT } from '../constants/uiState'

const router = useRouter()
const loading = ref(false)
const assistantLoading = ref(false)
const assistantOpen = ref(false)
const appSettings = reactive(createAppSettingsState())
const assistantInput = ref('')
const assistantMessages = ref([createAssistantWelcomeMessage()])
const assistantScrollRef = ref(null)

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
const heroTitle = computed(() => '机车博士')
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

function normalizeAssistantResponseText(text) {
  return String(text || '')
    .replace(/\r/g, '')
    .replace(/\s*(当前客户是|车辆为|当前工单|本次工单主诉是|当前已选项目包括|系统推荐下一步关注|接车快检记录为|下一步建议|应急建议|应急模式|重点关注|建议如下)[:：]\s*/g, '\n$1：')
    .replace(/(下一步建议|应急建议|应急模式|重点关注|建议如下)[:：]\s*(\d+[.、)])\s*/g, '$1：\n$2 ')
    .replace(/([。！？;；])\s*(\d+[.、)])\s*/g, '$1\n$2 ')
    .replace(/\n\s*(\d+[.、)])\s*/g, '\n$1 ')
    .trim()
}

function assistantResponseSummary(text) {
  const normalized = normalizeAssistantResponseText(text)
  if (!normalized) return []
  const lines = normalized.split('\n').map((line) => line.trim()).filter(Boolean)
  const summary = []
  for (const line of lines) {
    if (/^(当前客户是|车辆为|当前工单|本次工单主诉是|当前已选项目包括|系统推荐下一步关注|接车快检记录为|下一步建议|应急建议|应急模式|重点关注|建议如下)[:：]/.test(line)) {
      continue
    }
    if (/^\d+[.、)]\s*/.test(line)) {
      continue
    }
    summary.push(line)
    if (summary.length >= 1) break
  }
  return summary
}

function assistantResponseSections(text) {
  const normalized = normalizeAssistantResponseText(text)
  if (!normalized) return []

  const lines = normalized.split('\n').map((line) => line.trim()).filter(Boolean)
  const sections = []
  let current = null
  let summarySkipped = false

  const pushCurrent = () => {
    if (current && current.items.length) sections.push(current)
    current = null
  }

  const startSection = (title, kind = 'text') => {
    pushCurrent()
    current = { key: `${title}-${sections.length}`, title, kind, items: [] }
  }

  for (const line of lines) {
    const headingMatch = line.match(
      /^(当前客户是|车辆为|当前工单|本次工单主诉是|当前已选项目包括|系统推荐下一步关注|接车快检记录为|下一步建议|应急建议|应急模式|重点关注|建议如下)[:：]\s*(.*)$/,
    )
    if (headingMatch) {
      const title = headingMatch[1]
      const kind = /^(下一步建议|应急建议|重点关注|建议如下)$/.test(title) ? 'steps' : 'text'
      startSection(title, kind)
      if (headingMatch[2]) current.items.push(headingMatch[2])
      summarySkipped = true
      continue
    }

    const stepMatch = line.match(/^(\d+)[.、)]\s*(.*)$/)
    if (stepMatch) {
      if (!current || current.kind !== 'steps') {
        startSection('下一步建议', 'steps')
      }
      current.items.push(stepMatch[2] || line)
      summarySkipped = true
      continue
    }

    if (!summarySkipped) {
      summarySkipped = true
      continue
    }

    if (!current) {
      startSection('补充说明', 'text')
    }
    current.items.push(line)
  }

  pushCurrent()
  return sections
}

function makeAssistantMessageId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`
}

function createAssistantWelcomeMessage() {
  return {
    id: makeAssistantMessageId(),
    role: 'assistant',
    text: '这里会像聊天窗口一样记录对话。你可以直接问我今天先盯什么、哪台车最急，或者某张工单下一步怎么做。',
    meta: [
      { tone: 'info', label: '聊天历史' },
      { tone: 'muted', label: '底部输入' },
    ],
  }
}

function scrollAssistantToBottom() {
  nextTick(() => {
    const el = assistantScrollRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

function openAssistant() {
  assistantOpen.value = true
  scrollAssistantToBottom()
}

function closeAssistant() {
  assistantOpen.value = false
}

function clearAssistantConversation() {
  assistantMessages.value = [createAssistantWelcomeMessage()]
  assistantInput.value = ''
  assistantLoading.value = false
  scrollAssistantToBottom()
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
  assistantInput.value = `帮我总结${normalizedStoreName.value}今天最需要优先跟进的事项，并建议下一步。`
}

async function loadAppSettings() {
  if (!getAuthToken()) return
  try {
    const data = await request.get('/mp/settings')
    applyAppSettings(appSettings, data)
  } catch {
    applyAppSettings(appSettings)
  } finally {
    resetAssistantPrompt()
    if (assistantMessages.value.length === 1 && assistantMessages.value[0].role === 'assistant') {
      assistantMessages.value = [createAssistantWelcomeMessage()]
    }
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
  const message = String(assistantInput.value || '').trim()
  if (!message) {
    ElMessage.warning('请先输入问题')
    return
  }

  assistantOpen.value = true
  assistantMessages.value.push({
    id: makeAssistantMessageId(),
    role: 'user',
    text: message,
  })
  assistantInput.value = ''
  scrollAssistantToBottom()

  assistantLoading.value = true
  try {
    const data = await request.post('/ai/assistant/chat', {
      message,
      context: {
        store_overview: overview,
      },
    })
    assistantMessages.value.push({
      id: makeAssistantMessageId(),
      role: 'assistant',
      text: data?.response || 'AI 暂时没有返回内容。',
      suggested_actions: data?.suggested_actions || [],
      action_cards: data?.action_cards || [],
      sources: data?.sources || [],
      meta: buildAssistantMeta(data),
      prompt: message,
    })
  } catch (error) {
    assistantMessages.value.push({
      id: makeAssistantMessageId(),
      role: 'assistant',
      text: error?.message || 'AI 助手暂时不可用',
      meta: [{ tone: 'warn', label: '请求失败' }],
      prompt: message,
    })
    ElMessage.error(error?.message || 'AI 助手暂时不可用')
  } finally {
    assistantLoading.value = false
    scrollAssistantToBottom()
  }
}

function usePrompt(prompt) {
  assistantInput.value = prompt
  askAssistant()
}

function runActionSuggestion(prompt) {
  assistantInput.value = prompt
  askAssistant()
}

function retryMessage(message) {
  if (!message?.prompt) return
  assistantInput.value = message.prompt
  askAssistant()
}

async function copyMessage(message) {
  if (!message?.text) return
  try {
    await navigator.clipboard.writeText(message.text)
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

.hero-title {
  font-size: 36px;
  line-height: 1.25;
  font-weight: 700;
  color: #0f172a;
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
  grid-template-columns: repeat(2, minmax(0, 1fr));
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

.ai-float-trigger {
  position: fixed;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 40;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 14px 12px 14px 16px;
  border: none;
  border-radius: 18px 0 0 18px;
  background: linear-gradient(180deg, #0f172a 0%, #1f3b5b 100%);
  color: #fff;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.28);
  cursor: pointer;
}

.ai-float-trigger-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 12px;
  background: rgba(38, 149, 214, 0.18);
  color: #7dd3fc;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.ai-float-trigger-text {
  writing-mode: vertical-rl;
  text-orientation: mixed;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.ai-panel {
  position: fixed;
  top: 16px;
  right: 16px;
  bottom: 16px;
  width: min(440px, calc(100vw - 32px));
  z-index: 45;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 24px;
  border: 1px solid rgba(213, 229, 239, 0.96);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.22);
  backdrop-filter: blur(14px);
}

.ai-panel-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 18px 18px 14px;
  border-bottom: 1px solid #e3edf4;
}

.ai-panel-subtitle {
  color: #64748b;
  margin-top: 6px;
  font-size: 13px;
  line-height: 1.6;
}

.ai-panel-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.ai-panel-history {
  flex: 1;
  overflow: auto;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background:
    radial-gradient(circle at top, rgba(38, 149, 214, 0.05), transparent 34%),
    linear-gradient(180deg, rgba(248, 251, 254, 0.96), rgba(243, 248, 252, 0.98));
}

.ai-message {
  display: flex;
}

.ai-message-user {
  justify-content: flex-end;
}

.ai-message-assistant {
  justify-content: flex-start;
}

.ai-message-bubble {
  max-width: 100%;
  display: grid;
  gap: 10px;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid #d7e4ee;
  background: #fff;
  color: #0f172a;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
}

.ai-message-user .ai-message-bubble {
  background: linear-gradient(180deg, #0f6cbd 0%, #2d9cdb 100%);
  color: #fff;
  border-color: transparent;
  border-bottom-right-radius: 6px;
}

.ai-message-assistant .ai-message-bubble {
  border-bottom-left-radius: 6px;
}

.ai-message-text {
  white-space: pre-wrap;
  line-height: 1.72;
  font-size: 14px;
}

.assistant-response-stack {
  display: grid;
  gap: 10px;
}

.assistant-summary-card {
  display: grid;
  gap: 6px;
  padding: 12px 14px;
  border-radius: 14px;
  background: linear-gradient(180deg, #f1f7ff 0%, #ffffff 100%);
  border: 1px solid #cfe0fb;
}

.assistant-summary-label {
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.assistant-summary-text {
  color: #0f172a;
  line-height: 1.7;
  font-size: 14px;
}

.assistant-response-section {
  display: grid;
  gap: 8px;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid #dbe7f2;
  background: #f8fbfe;
}

.assistant-response-section-steps {
  background: linear-gradient(180deg, #fffaf2 0%, #ffffff 100%);
  border-color: #f2d7a8;
}

.assistant-response-section-text {
  background: #f8fbfe;
}

.assistant-response-section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.assistant-response-section-head strong {
  color: #0f172a;
  font-size: 14px;
}

.assistant-response-section-head span {
  color: #64748b;
  font-size: 12px;
  white-space: nowrap;
}

.assistant-response-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 6px;
  color: #1f2937;
  line-height: 1.7;
}

.assistant-response-text {
  display: grid;
  gap: 8px;
  color: #334155;
  line-height: 1.72;
}

.assistant-response-text p {
  margin: 0;
}

.ai-message-pending {
  border-style: dashed;
  background: linear-gradient(180deg, #f8fbff 0%, #eef6fd 100%);
}

.ai-message-pending strong {
  color: #0f172a;
}

.ai-message-pending span {
  color: #64748b;
  line-height: 1.6;
}

.ai-message-tools {
  display: flex;
  gap: 4px;
  justify-content: flex-end;
}

.ai-panel-composer {
  display: grid;
  gap: 12px;
  padding: 16px 18px 18px;
  border-top: 1px solid #e3edf4;
  background: rgba(255, 255, 255, 0.98);
}

.ai-composer-input :deep(.el-textarea__inner) {
  min-height: 88px;
  border-radius: 16px;
  padding: 14px 16px;
  resize: none;
}

.ai-panel-submit {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.ai-panel-hint {
  color: #7a8ca1;
  font-size: 12px;
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

  .ai-float-trigger {
    top: auto;
    right: 16px;
    bottom: 16px;
    transform: none;
    border-radius: 999px;
    padding: 12px 14px;
  }

  .ai-float-trigger-text {
    writing-mode: horizontal-tb;
    text-orientation: initial;
    letter-spacing: 0.04em;
  }
}

@media (max-width: 720px) {
  .ai-float-trigger {
    padding: 10px 12px;
  }

  .ai-float-trigger-text {
    display: none;
  }
}
</style>
