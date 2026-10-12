<template>
  <div class="shop-page">
    <div class="card page-head">
      <div>
        <h2>商城中心</h2>
        <p>{{ headText }}</p>
      </div>
      <div class="head-actions">
        <el-button plain @click="$router.push('/inventory')">去库存中心维护</el-button>
        <el-button type="primary" :loading="loading" @click="reloadAll">刷新预览</el-button>
      </div>
    </div>

    <div class="summary-grid">
      <div class="card summary-card"><span>可售配件</span><strong>{{ stats.parts }}</strong></div>
      <div class="card summary-card"><span>推荐服务</span><strong>{{ stats.services }}</strong></div>
      <div class="card summary-card"><span>服务套餐</span><strong>{{ stats.packages }}</strong></div>
      <div class="card summary-card"><span>支持车型</span><strong>{{ stats.models }}</strong></div>
    </div>

    <div class="card">
      <div class="toolbar toolbar--shop">
        <el-select v-model="filters.brand" clearable filterable placeholder="品牌" style="width: 180px" @change="onBrandChange">
          <el-option v-for="item in vehicleBrands" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filters.model_id" clearable filterable placeholder="车型" style="width: 280px" @change="onModelChange">
          <el-option
            v-for="item in modelOptions"
            :key="item.id"
            :label="modelLabel(item)"
            :value="item.id"
          />
        </el-select>
        <el-select v-model="filters.kind" clearable placeholder="商品类型" style="width: 160px" @change="reloadShopPreview">
          <el-option label="配件" value="part" />
          <el-option label="服务" value="service" />
          <el-option label="套餐" value="package" />
        </el-select>
        <el-input v-model="filters.keyword" clearable placeholder="搜索商品名称/编号/说明" style="width: 260px" @keyup.enter="reloadShopPreview" />
        <el-button type="primary" @click="reloadShopPreview">查询</el-button>
        <el-button @click="resetFilters">重置</el-button>
      </div>

      <el-alert
        :title="previewHint"
        type="info"
        :closable="false"
        show-icon
        class="page-alert"
      />

      <el-tabs v-model="activeTab">
        <el-tab-pane label="商城预览" name="preview">
          <div class="shop-preview-grid" v-loading="previewLoading">
            <div class="preview-panel preview-panel--catalog">
              <div class="panel-title">小程序商品预览</div>
              <div class="catalog-toolbar">
                <span>共 {{ previewItems.length }} 件商品</span>
                <span>点击商品卡片查看详情</span>
              </div>
              <div v-if="previewItems.length" class="catalog-grid">
                <button
                  v-for="item in previewItems"
                  :key="`${item.product_type}-${item.id}`"
                  type="button"
                  class="product-card"
                  @click="openProductDetail(item)"
                >
                  <div class="product-card__image-wrap">
                    <img class="product-card__image" :src="productCover(item)" :alt="item.name" />
                    <el-tag size="small" effect="light" class="product-card__tag">{{ item.product_type_label }}</el-tag>
                  </div>
                  <div class="product-card__body">
                    <div class="product-card__name">{{ item.name }}</div>
                    <div class="product-card__desc">{{ item.description || item.summary || '暂无说明' }}</div>
                    <div class="product-card__foot">
                      <strong class="product-card__price">{{ priceText(item.price) }}</strong>
                      <span v-if="item.category" class="product-card__category">{{ item.category }}</span>
                    </div>
                  </div>
                </button>
              </div>
              <div v-else class="empty-state">当前条件下没有可展示的商城商品。</div>
            </div>

            <div class="preview-panel">
              <div class="panel-title">选中车型信息</div>
              <div v-if="selectedModel" class="model-summary">
                <div class="model-summary__name">{{ modelLabel(selectedModel) }}</div>
                <div class="model-summary__meta">
                  <span>{{ selectedModel.year_from }} - {{ selectedModel.year_to }}</span>
                  <span>{{ selectedModel.category || '未分类' }}</span>
                  <span>{{ selectedModel.displacement_cc || '--' }} cc</span>
                </div>
                <div class="model-summary__desc">
                  这里的商品会同时影响小程序商城、推荐保养和预约草稿。先在库存中心维护，再回到这里看最终呈现。
                </div>
                <el-button class="model-summary__btn" plain @click="activeTab = 'manage'">去商城运营改商品</el-button>
              </div>
              <div v-else class="empty-state">请选择一个标准车型，才能预览对应商品。</div>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="商城运营" name="manage">
          <div class="ops-toolbar">
            <div class="ops-toolbar__left">
              <el-switch
                v-model="showInactive"
                inline-prompt
                active-text="显示全部"
                inactive-text="仅上架"
              />
              <span class="ops-toolbar__hint">可直接修改上架状态、售价和排序，保存后同步到小程序商城。</span>
            </div>
            <el-button plain :loading="loading" @click="reloadShopPreview">刷新运营数据</el-button>
          </div>

          <div class="manage-stack">
            <section class="manage-section">
              <div class="section-head">
                <div>
                  <h3>配件上架</h3>
                  <p>调整售卖状态、价格和库存，让客户侧立即看到最新商品。</p>
                </div>
                <div class="section-actions">
                  <el-tag effect="plain">共 {{ visiblePartRows.length }} 条</el-tag>
                  <el-button size="small" @click="toggleVisibleRows('part', true)">批量上架</el-button>
                  <el-button size="small" @click="toggleVisibleRows('part', false)">批量下架</el-button>
                  <el-button size="small" type="primary" :loading="batchSaving.part" @click="saveVisibleRows('part')">保存全部</el-button>
                </div>
              </div>
              <el-table
                :data="visiblePartRows"
                v-loading="partLoading"
                :empty-text="EMPTY_TEXT.parts"
                size="small"
                style="width: 100%"
              >
                <el-table-column label="状态" width="110">
                  <template #default="scope">
                    <el-switch
                      v-model="scope.row.is_active"
                      inline-prompt
                      active-text="上架"
                      inactive-text="下架"
                    />
                  </template>
                </el-table-column>
                <el-table-column prop="part_no" label="料号" width="160" />
                <el-table-column prop="name" label="名称" min-width="180" />
                <el-table-column prop="brand" label="品牌" width="120" />
                <el-table-column prop="category" label="分类" width="120" />
                <el-table-column label="售价" width="140">
                  <template #default="scope">
                    <el-input-number
                      v-model="scope.row.sale_price"
                      :min="0"
                      :precision="2"
                      controls-position="right"
                      style="width: 100%"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="库存" width="120">
                  <template #default="scope">
                    <el-input-number
                      v-model="scope.row.stock_qty"
                      :min="0"
                      :precision="0"
                      controls-position="right"
                      style="width: 100%"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="兼容车型" width="110">
                  <template #default="scope">
                    {{ scope.row.compatible_model_ids?.length || 0 }} 项
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="110" fixed="right">
                  <template #default="scope">
                    <el-button size="small" type="primary" :loading="rowSaving('part', scope.row.id)" @click="savePartRow(scope.row)">
                      保存
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </section>

            <section class="manage-section">
              <div class="section-head">
                <div>
                  <h3>标准项目</h3>
                  <p>排序决定小程序中的展示顺序，价格和状态一起保存。</p>
                </div>
                <div class="section-actions">
                  <el-tag effect="plain">共 {{ visibleServiceRows.length }} 条</el-tag>
                  <el-button size="small" @click="toggleVisibleRows('service', true)">批量上架</el-button>
                  <el-button size="small" @click="toggleVisibleRows('service', false)">批量下架</el-button>
                  <el-button size="small" type="primary" :loading="batchSaving.service" @click="saveVisibleRows('service')">保存全部</el-button>
                </div>
              </div>
              <el-table
                :data="visibleServiceRows"
                v-loading="serviceLoading"
                :empty-text="EMPTY_TEXT.serviceItems"
                size="small"
                style="width: 100%"
              >
                <el-table-column label="状态" width="110">
                  <template #default="scope">
                    <el-switch
                      v-model="scope.row.is_active"
                      inline-prompt
                      active-text="上架"
                      inactive-text="下架"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="排序" width="130">
                  <template #default="scope">
                    <el-input-number
                      v-model="scope.row.sort_order"
                      :min="0"
                      :step="10"
                      controls-position="right"
                      style="width: 100%"
                    />
                  </template>
                </el-table-column>
                <el-table-column prop="service_code" label="编码" width="150" />
                <el-table-column prop="service_name" label="名称" min-width="180" />
                <el-table-column label="建议价" width="140">
                  <template #default="scope">
                    <el-input-number
                      v-model="scope.row.suggested_price"
                      :min="0"
                      :precision="2"
                      controls-position="right"
                      style="width: 100%"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="工时" width="110">
                  <template #default="scope">
                    <el-input-number
                      v-model="scope.row.labor_hours"
                      :min="0"
                      :precision="1"
                      :step="0.5"
                      controls-position="right"
                      style="width: 100%"
                    />
                  </template>
                </el-table-column>
                <el-table-column prop="repair_method" label="维修方法" min-width="240" show-overflow-tooltip />
                <el-table-column label="操作" width="110" fixed="right">
                  <template #default="scope">
                    <el-button size="small" type="primary" :loading="rowSaving('service', scope.row.id)" @click="saveServiceRow(scope.row)">
                      保存
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </section>

            <section class="manage-section">
              <div class="section-head">
                <div>
                  <h3>服务套餐</h3>
                  <p>套餐顺序、价格和启用状态都会同步到商城首页和推荐位。</p>
                </div>
                <div class="section-actions">
                  <el-tag effect="plain">共 {{ visiblePackageRows.length }} 条</el-tag>
                  <el-button size="small" @click="toggleVisibleRows('package', true)">批量上架</el-button>
                  <el-button size="small" @click="toggleVisibleRows('package', false)">批量下架</el-button>
                  <el-button size="small" type="primary" :loading="batchSaving.package" @click="saveVisibleRows('package')">保存全部</el-button>
                </div>
              </div>
              <el-table
                :data="visiblePackageRows"
                v-loading="packageLoading"
                :empty-text="EMPTY_TEXT.servicePackages"
                size="small"
                style="width: 100%"
              >
                <el-table-column label="状态" width="110">
                  <template #default="scope">
                    <el-switch
                      v-model="scope.row.is_active"
                      inline-prompt
                      active-text="上架"
                      inactive-text="下架"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="排序" width="130">
                  <template #default="scope">
                    <el-input-number
                      v-model="scope.row.sort_order"
                      :min="0"
                      :step="10"
                      controls-position="right"
                      style="width: 100%"
                    />
                  </template>
                </el-table-column>
                <el-table-column prop="package_code" label="编码" width="150" />
                <el-table-column prop="package_name" label="套餐名称" min-width="180" />
                <el-table-column label="推荐周期" width="160">
                  <template #default="scope">
                    <span>{{ scope.row.interval_label || '--' }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="建议总价" width="140">
                  <template #default="scope">
                    <el-input-number
                      v-model="scope.row.suggested_price_total"
                      :min="0"
                      :precision="2"
                      controls-position="right"
                      style="width: 100%"
                    />
                  </template>
                </el-table-column>
                <el-table-column label="项目数" width="100">
                  <template #default="scope">
                    {{ scope.row.item_count || scope.row.items?.length || 0 }} 项
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="110" fixed="right">
                  <template #default="scope">
                    <el-button size="small" type="primary" :loading="rowSaving('package', scope.row.id)" @click="savePackageRow(scope.row)">
                      保存
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </section>
          </div>
        </el-tab-pane>
      </el-tabs>

      <el-drawer
        v-model="detailVisible"
        size="480px"
        :title="selectedPreviewItem?.name || '商品详情'"
        direction="rtl"
      >
        <div v-if="selectedPreviewItem" class="product-detail">
          <div class="product-detail__hero">
            <img class="product-detail__image" :src="productCover(selectedPreviewItem)" :alt="selectedPreviewItem.name" />
            <div class="product-detail__hero-body">
              <div class="product-detail__price">{{ priceText(selectedPreviewItem.price) }}</div>
              <div class="product-detail__meta">
                <el-tag effect="plain">{{ selectedPreviewItem.product_type_label }}</el-tag>
                <el-tag v-if="selectedPreviewItem.category" effect="plain">{{ selectedPreviewItem.category }}</el-tag>
                <el-tag v-if="selectedPreviewItem.brand" effect="plain">{{ selectedPreviewItem.brand }}</el-tag>
              </div>
              <div class="product-detail__section product-detail__section--intro">
                <div class="product-detail__label">商品说明</div>
                <p>{{ selectedPreviewItem.description || selectedPreviewItem.summary || '暂无说明' }}</p>
              </div>
              <div class="product-detail__section">
                <div class="product-detail__label">适用车型</div>
                <p>{{ selectedModelLabel || '当前未选择车型' }}</p>
              </div>
            </div>
          </div>
          <div v-if="selectedPreviewItem.product_type === 'part'" class="product-detail__section">
            <div class="product-detail__label">配件信息</div>
            <p>料号：{{ selectedPreviewItem.part_no || '--' }}</p>
            <p>库存：{{ selectedPreviewItem.stock_qty ?? '--' }}</p>
            <p>是否上架：{{ selectedPreviewItem.is_active === false ? '下架' : '上架' }}</p>
          </div>
          <div v-else-if="selectedPreviewItem.product_type === 'service'" class="product-detail__section">
            <div class="product-detail__label">标准项目</div>
            <p>编码：{{ selectedPreviewItem.service_code || '--' }}</p>
            <p>工时：{{ selectedPreviewItem.labor_hours ?? '--' }}</p>
            <p>排序：{{ selectedPreviewItem.sort_order ?? '--' }}</p>
          </div>
          <div v-if="selectedPreviewItem.product_type === 'service' && (selectedPreviewItem.repair_method || selectedPreviewItem.notes)" class="product-detail__section">
            <div class="product-detail__label">维修方法</div>
            <p>{{ selectedPreviewItem.repair_method || selectedPreviewItem.notes || '暂无维修方法' }}</p>
          </div>
          <div v-else class="product-detail__section">
            <div class="product-detail__label">服务套餐</div>
            <p>编码：{{ selectedPreviewItem.package_code || '--' }}</p>
            <p>周期：{{ selectedPreviewItem.interval_label || '--' }}</p>
            <p>项目数：{{ selectedPreviewItem.item_count || selectedPreviewItem.items?.length || 0 }}</p>
          </div>
        </div>
      </el-drawer>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../utils/request'
import { EMPTY_TEXT } from '../constants/uiState'

const loading = ref(false)
const previewLoading = ref(false)
const activeTab = ref('preview')
const showInactive = ref(false)
const vehicleBrands = ref([])
const vehicleModels = ref([])
const partRows = ref([])
const serviceRows = ref([])
const packageRows = ref([])
const previewItems = ref([])
const selectedPreviewItem = ref(null)
const detailVisible = ref(false)
const partLoading = ref(false)
const serviceLoading = ref(false)
const packageLoading = ref(false)
const batchSaving = reactive({
  part: false,
  service: false,
  package: false,
})
const savingState = reactive({
  part: {},
  service: {},
  package: {},
})

const filters = reactive({
  brand: '',
  model_id: null,
  kind: '',
  keyword: '',
})

const stats = reactive({
  parts: 0,
  services: 0,
  packages: 0,
  models: 0,
})

const selectedModel = computed(() => vehicleModels.value.find((item) => item.id === filters.model_id) || null)
const selectedModelLabel = computed(() => (selectedModel.value ? modelLabel(selectedModel.value) : ''))
const modelOptions = computed(() => {
  if (!filters.brand) return vehicleModels.value
  return vehicleModels.value.filter((item) => item.brand === filters.brand)
})
const visiblePartRows = computed(() => (showInactive.value ? partRows.value : partRows.value.filter((item) => item.is_active !== false)))
const visibleServiceRows = computed(() => (showInactive.value ? serviceRows.value : serviceRows.value.filter((item) => item.is_active !== false)))
const visiblePackageRows = computed(() => (showInactive.value ? packageRows.value : packageRows.value.filter((item) => item.is_active !== false)))

const headText = computed(() =>
  selectedModel.value
    ? `当前预览车型：${selectedModel.value.brand} ${selectedModel.value.model_name}，查看它在商城里会被呈现成哪些商品。`
    : '这里把后台维护的配件、服务项目和套餐聚合成小程序商城视图。'
)

const previewHint = computed(() =>
  selectedModel.value
    ? '这里展示的就是客户侧商城会看到的商品形态，改完库存中心后回来看这里最直观。'
    : '先选一个标准车型，商城预览会按车型展示套餐、服务和可售配件。'
)

function productTypeText(value) {
  const map = {
    part: '配件',
    service: '服务',
    package: '套餐',
  }
  return map[value] || '商品'
}

function priceText(value) {
  const num = Number(value)
  if (!Number.isFinite(num)) return '--'
  return `¥${num.toFixed(2)}`
}

function modelLabel(item) {
  if (!item) return ''
  return `${item.brand} ${item.model_name} ${item.year_from}-${item.year_to}`
}

function buildCoverSeed(text) {
  return String(text || 'DrMoto').split('').reduce((acc, ch) => {
    return (acc * 31 + ch.charCodeAt(0)) % 360
  }, 0)
}

function productCover(item) {
  const label = item?.name || item?.product_type_label || 'DrMoto'
  const hue = buildCoverSeed(label)
  const accent = item?.product_type === 'part' ? '#ff7a45' : item?.product_type === 'package' ? '#7c4dff' : '#1890ff'
  const bg = `hsl(${hue}, 75%, 94%)`
  const bg2 = `hsl(${(hue + 28) % 360}, 85%, 86%)`
  const tag = item?.product_type_label || '商品'
  const text = label.length > 10 ? `${label.slice(0, 10)}…` : label
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="600" height="600" viewBox="0 0 600 600">
      <defs>
        <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="${bg}" />
          <stop offset="100%" stop-color="${bg2}" />
        </linearGradient>
      </defs>
      <rect width="600" height="600" fill="url(#g)" rx="48"/>
      <circle cx="470" cy="120" r="100" fill="${accent}" fill-opacity="0.14"/>
      <circle cx="130" cy="470" r="150" fill="${accent}" fill-opacity="0.10"/>
      <rect x="66" y="70" width="130" height="46" rx="23" fill="#ffffff" fill-opacity="0.92"/>
      <text x="131" y="101" font-size="24" font-family="PingFang SC, Microsoft YaHei, Arial" text-anchor="middle" fill="${accent}" font-weight="700">${tag}</text>
      <text x="300" y="314" font-size="52" font-family="PingFang SC, Microsoft YaHei, Arial" text-anchor="middle" fill="#0f172a" font-weight="700">${text}</text>
      <text x="300" y="372" font-size="22" font-family="PingFang SC, Microsoft YaHei, Arial" text-anchor="middle" fill="#475569">${item?.category || item?.brand || 'DrMoto'} </text>
      <text x="300" y="466" font-size="26" font-family="PingFang SC, Microsoft YaHei, Arial" text-anchor="middle" fill="#475569">点击查看详情</text>
    </svg>
  `.trim()
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`
}

function openProductDetail(item) {
  selectedPreviewItem.value = item
  detailVisible.value = true
}

function rowSaving(kind, id) {
  return Boolean(savingState[kind]?.[id])
}

function setRowSaving(kind, id, value) {
  if (!savingState[kind]) savingState[kind] = {}
  if (value) {
    savingState[kind][id] = true
    return
  }
  delete savingState[kind][id]
}

function normalizeNumber(value) {
  if (value === '' || value === null || value === undefined) return null
  const num = Number(value)
  return Number.isFinite(num) ? num : null
}

function buildServiceParts(items = []) {
  return items.map((item, index) => ({
    part_id: item.part_id || null,
    part_no: item.part_no || null,
    part_name: item.part_name,
    qty: normalizeNumber(item.qty) ?? 1,
    unit_price: normalizeNumber(item.unit_price),
    notes: item.notes || null,
    sort_order: normalizeNumber(item.sort_order) ?? ((index + 1) * 10),
    is_optional: Boolean(item.is_optional),
  }))
}

function buildPackageItems(items = []) {
  return items.map((item, index) => ({
    template_item_id: item.template_item_id || item.service_item?.id,
    sort_order: normalizeNumber(item.sort_order) ?? ((index + 1) * 10),
    is_optional: Boolean(item.is_optional),
    notes: item.notes || null,
  }))
}

async function loadBrands() {
  vehicleBrands.value = await request.get('/mp/catalog/vehicle-models/brands', { params: { active_only: true } })
}

async function loadModels() {
  const res = await request.get('/mp/catalog/vehicle-models', {
    params: {
      page: 1,
      size: 200,
      brand: filters.brand || '',
      model_name: '',
      category: '',
      keyword: '',
    },
  })
  vehicleModels.value = Array.isArray(res?.items) ? res.items : []
  stats.models = Number(res?.total || vehicleModels.value.length || 0)
  if (filters.model_id && !vehicleModels.value.some((item) => item.id === filters.model_id)) {
    filters.model_id = null
  }
  if (!filters.model_id && vehicleModels.value.length) {
    filters.model_id = vehicleModels.value[0].id
  }
}

async function loadParts() {
  partLoading.value = true
  try {
    const res = await request.get('/mp/catalog/parts', {
      params: {
        page: 1,
        size: 100,
        category: '',
        keyword: filters.keyword || '',
        active_only: false,
      },
    })
    const rows = Array.isArray(res?.items) ? res.items : []
    partRows.value = rows
    stats.parts = Number(res?.total || rows.length || 0)
    return rows
  } finally {
    partLoading.value = false
  }
}

async function loadModelShopData() {
  if (!selectedModel.value) {
    serviceRows.value = []
    packageRows.value = []
    stats.services = 0
    stats.packages = 0
    return { services: [], packages: [] }
  }

  serviceLoading.value = true
  packageLoading.value = true
  try {
    const [services, packages] = await Promise.all([
      request.get(`/mp/catalog/vehicle-models/${selectedModel.value.id}/service-items`, { params: { active_only: false } }),
      request.get(`/mp/catalog/vehicle-models/${selectedModel.value.id}/service-packages`, { params: { active_only: false } }),
    ])
    const serviceList = Array.isArray(services) ? services : []
    const packageList = Array.isArray(packages) ? packages : []
    serviceRows.value = serviceList
    packageRows.value = packageList
    stats.services = serviceList.length
    stats.packages = packageList.length
    return { services: serviceList, packages: packageList }
  } finally {
    serviceLoading.value = false
    packageLoading.value = false
  }
}

function buildPreviewItems(parts = [], services = [], packages = []) {
  const activeParts = (parts || []).filter((item) => item.is_active !== false)
  const activeServices = (services || []).filter((item) => item.is_active !== false)
  const activePackages = (packages || []).filter((item) => item.is_active !== false)
  return [
    ...activePackages.map((item) => ({
      ...item,
      product_type: 'package',
      product_type_label: productTypeText('package'),
      name: item.package_name,
      description: item.description || item.interval_label || '套餐商品',
      price: item.suggested_price_total,
    })),
    ...activeServices.map((item) => ({
      ...item,
      product_type: 'service',
      product_type_label: productTypeText('service'),
      name: item.service_name,
      description: item.repair_method || '服务项目',
      price: item.suggested_price,
    })),
    ...activeParts.slice(0, 6).map((item) => ({
      ...item,
      product_type: 'part',
      product_type_label: productTypeText('part'),
      name: item.name,
      description: item.brand || item.category || '配件商品',
      price: item.sale_price,
    })),
  ]
}

async function reloadShopPreview() {
  previewLoading.value = true
  try {
    const [parts, modelData] = await Promise.all([
      loadParts(),
      loadModelShopData(),
    ])
    const services = Array.isArray(modelData?.services) ? modelData.services : []
    const packages = Array.isArray(modelData?.packages) ? modelData.packages : []
    let rows = buildPreviewItems(parts, services, packages)
    if (filters.kind) {
      rows = rows.filter((item) => item.product_type === filters.kind)
    }
    if (filters.keyword) {
      const keyword = String(filters.keyword).trim().toLowerCase()
      rows = rows.filter((item) => {
        const text = [
          item.name,
          item.description,
          item.summary,
          item.part_no,
          item.service_code,
          item.package_code,
          item.brand,
          item.category,
          item.interval_label,
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
        return text.includes(keyword)
      })
    }
    previewItems.value = rows
  } finally {
    previewLoading.value = false
  }
}

async function savePartRow(row, options = {}) {
  const { reload = true, quiet = false } = options
  setRowSaving('part', row.id, true)
  try {
    await request.put(`/mp/catalog/parts/${row.id}`, {
      part_no: row.part_no,
      name: row.name,
      brand: row.brand || null,
      category: row.category || null,
      unit: row.unit || '件',
      compatible_model_ids: Array.isArray(row.compatible_model_ids) ? row.compatible_model_ids : [],
      min_stock: normalizeNumber(row.min_stock),
      sale_price: normalizeNumber(row.sale_price),
      cost_price: normalizeNumber(row.cost_price),
      stock_qty: normalizeNumber(row.stock_qty),
      supplier_name: row.supplier_name || null,
      is_active: Boolean(row.is_active),
    })
    if (!quiet) ElMessage.success('配件已保存')
    if (reload) await reloadShopPreview()
  } finally {
    setRowSaving('part', row.id, false)
  }
}

async function saveServiceRow(row, options = {}) {
  const { reload = true, quiet = false } = options
  setRowSaving('service', row.id, true)
  try {
    await request.put(`/mp/catalog/vehicle-models/${row.model_id}/service-items/${row.id}`, {
      service_name: row.service_name,
      service_code: row.service_code || null,
      repair_method: row.repair_method || null,
      labor_hours: normalizeNumber(row.labor_hours),
      labor_price: normalizeNumber(row.labor_price),
      suggested_price: normalizeNumber(row.suggested_price),
      notes: row.notes || null,
      sort_order: normalizeNumber(row.sort_order) ?? 100,
      is_active: Boolean(row.is_active),
      required_parts: buildServiceParts(row.required_parts || []),
    })
    if (!quiet) ElMessage.success('标准项目已保存')
    if (reload) await reloadShopPreview()
  } finally {
    setRowSaving('service', row.id, false)
  }
}

async function savePackageRow(row, options = {}) {
  const { reload = true, quiet = false } = options
  setRowSaving('package', row.id, true)
  try {
    await request.put(`/mp/catalog/vehicle-models/${row.model_id}/service-packages/${row.id}`, {
      package_name: row.package_name,
      package_code: row.package_code || null,
      description: row.description || null,
      recommended_interval_km: normalizeNumber(row.recommended_interval_km),
      recommended_interval_months: normalizeNumber(row.recommended_interval_months),
      labor_hours_total: normalizeNumber(row.labor_hours_total),
      labor_price_total: normalizeNumber(row.labor_price_total),
      parts_price_total: normalizeNumber(row.parts_price_total),
      suggested_price_total: normalizeNumber(row.suggested_price_total),
      sort_order: normalizeNumber(row.sort_order) ?? 100,
      is_active: Boolean(row.is_active),
      items: buildPackageItems(row.items || []),
    })
    if (!quiet) ElMessage.success('服务套餐已保存')
    if (reload) await reloadShopPreview()
  } finally {
    setRowSaving('package', row.id, false)
  }
}

async function saveVisibleRows(kind) {
  const rowsMap = {
    part: visiblePartRows.value,
    service: visibleServiceRows.value,
    package: visiblePackageRows.value,
  }
  const rows = rowsMap[kind] || []
  if (!rows.length) {
    ElMessage.info('当前没有可保存的记录')
    return
  }
  batchSaving[kind] = true
  try {
    for (const row of rows) {
      if (kind === 'part') {
        // eslint-disable-next-line no-await-in-loop
        await savePartRow(row, { reload: false, quiet: true })
      } else if (kind === 'service') {
        // eslint-disable-next-line no-await-in-loop
        await saveServiceRow(row, { reload: false, quiet: true })
      } else if (kind === 'package') {
        // eslint-disable-next-line no-await-in-loop
        await savePackageRow(row, { reload: false, quiet: true })
      }
    }
    await reloadShopPreview()
    ElMessage.success('当前列表已全部保存')
  } finally {
    batchSaving[kind] = false
  }
}

function toggleVisibleRows(kind, value) {
  const rowsMap = {
    part: visiblePartRows.value,
    service: visibleServiceRows.value,
    package: visiblePackageRows.value,
  }
  const rows = rowsMap[kind] || []
  rows.forEach((row) => {
    row.is_active = value
  })
  ElMessage.success(value ? '已批量设为上架' : '已批量设为下架')
}

async function reloadAll() {
  loading.value = true
  try {
    await Promise.all([loadBrands(), loadModels()])
    await reloadShopPreview()
  } finally {
    loading.value = false
  }
}

async function onBrandChange() {
  filters.model_id = null
  await loadModels()
  await reloadShopPreview()
}

async function onModelChange() {
  await reloadShopPreview()
}

function resetFilters() {
  filters.brand = ''
  filters.model_id = null
  filters.kind = ''
  filters.keyword = ''
  showInactive.value = false
  reloadAll()
}

onMounted(async () => {
  await reloadAll()
})
</script>

<style scoped>
.shop-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.page-head h2 {
  margin: 0 0 6px;
}

.page-head p {
  margin: 0;
  color: #64748b;
  line-height: 1.7;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(120px, 1fr));
  gap: 12px;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.summary-card span {
  color: #64748b;
  font-size: 12px;
}

.summary-card strong {
  font-size: 28px;
  color: #0f172a;
}

.page-alert {
  margin-top: 12px;
}

.head-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar {
  margin-bottom: 14px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.toolbar--shop {
  align-items: flex-start;
}

.ops-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border: 1px solid #e6eef9;
}

.ops-toolbar__left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.ops-toolbar__hint {
  color: #6b7280;
  font-size: 13px;
}

.manage-stack {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin-top: 16px;
}

.manage-section {
  border: 1px solid #e9eef6;
  border-radius: 16px;
  padding: 14px;
  background: #fff;
}

.section-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.section-head h3 {
  margin: 0 0 6px;
  font-size: 16px;
}

.section-head p {
  margin: 0;
  color: #6b7280;
  line-height: 1.6;
  font-size: 13px;
}

.shop-preview-grid {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 16px;
  margin-top: 16px;
}

.preview-panel {
  border: 1px solid #ebeef5;
  border-radius: 14px;
  padding: 16px;
  background: #fff;
}

.preview-panel--catalog {
  background: linear-gradient(180deg, #ffffff 0%, #fbfbfd 100%);
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 14px;
}

.catalog-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
  color: #64748b;
  font-size: 13px;
}

.catalog-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.product-card {
  appearance: none;
  border: 1px solid #edf1f7;
  border-radius: 16px;
  padding: 0;
  background: #fff;
  overflow: hidden;
  text-align: left;
  cursor: pointer;
  box-shadow: 0 8px 30px rgba(15, 23, 42, 0.04);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.product-card:hover {
  transform: translateY(-2px);
  border-color: #cfe0ff;
  box-shadow: 0 14px 36px rgba(24, 144, 255, 0.12);
}

.product-card__image-wrap {
  position: relative;
  aspect-ratio: 1 / 1;
  background: #f8fafc;
}

.product-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.product-card__tag {
  position: absolute;
  left: 12px;
  top: 12px;
}

.product-card__body {
  padding: 12px 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.product-card__name {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.4;
  color: #0f172a;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  min-height: 42px;
}

.product-card__desc {
  font-size: 13px;
  color: #64748b;
  line-height: 1.55;
  min-height: 42px;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.product-card__foot,
.model-summary__meta,
.product-detail__meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.model-summary__desc {
  margin: 10px 0 0;
  color: #667085;
  line-height: 1.6;
}

.model-summary {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.model-summary__name {
  font-size: 18px;
  font-weight: 700;
}

.model-summary__meta {
  flex-wrap: wrap;
  color: #6b7280;
  font-size: 13px;
}

.model-summary__btn {
  align-self: flex-start;
  margin-top: 8px;
}

.product-card__price {
  color: #d61f1f;
  font-size: 18px;
}

.product-card__category {
  color: #94a3b8;
  font-size: 12px;
}

.product-detail {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.product-detail__hero {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.product-detail__hero-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.product-detail__image {
  width: 100%;
  aspect-ratio: 1 / 1;
  object-fit: cover;
  border-radius: 18px;
  border: 1px solid #edf1f7;
}

.product-detail__price {
  font-size: 26px;
  font-weight: 700;
  color: #d61f1f;
}

.product-detail__meta {
  flex-wrap: wrap;
}

.product-detail__section {
  padding: 14px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
}

.product-detail__section--intro {
  background: linear-gradient(180deg, #f8fbff 0%, #f5f9ff 100%);
}

.product-detail__label {
  margin-bottom: 8px;
  font-weight: 600;
  color: #0f172a;
}

.product-detail__section p {
  margin: 4px 0;
  color: #475569;
  line-height: 1.6;
}

.empty-state {
  padding: 30px 12px;
  text-align: center;
  color: #8a94a6;
}

@media (max-width: 1280px) {
  .shop-preview-grid {
    grid-template-columns: 1fr;
  }

  .catalog-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(120px, 1fr));
  }

  .page-head,
  .toolbar,
  .ops-toolbar,
  .section-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .catalog-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .catalog-grid {
    grid-template-columns: 1fr;
  }

  .product-detail__hero {
    grid-template-columns: 1fr;
  }
}
</style>
