<template>
  <div class="trial-inbox">
    <div class="page-head">
      <div>
        <h2>试运营待办</h2>
        <p>官网线索和客户小程序预约统一进入这里，确认后转成门店工单。</p>
      </div>
      <el-button type="primary" :loading="loading" @click="loadInbox">刷新</el-button>
    </div>

    <el-alert
      title="官网线索转工单时，需要先在客户库确认客户 ID 和车牌；小程序预约会自动带入客户和车辆。"
      type="info"
      show-icon
      :closable="false"
      class="page-tip"
    />

    <el-table :data="items" v-loading="loading" empty-text="暂无待办" style="width: 100%">
      <el-table-column label="来源" width="120">
        <template #default="{ row }">
          <el-tag :type="row.source_type === 'lead' ? 'warning' : 'primary'" effect="plain">
            {{ row.source_type === 'lead' ? '官网线索' : '小程序预约' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="主题/姓名" min-width="160" />
      <el-table-column prop="contact" label="联系方式/客户" min-width="150" />
      <el-table-column prop="vehicle_plate" label="车牌" width="130" />
      <el-table-column prop="message" label="诉求" min-width="260" show-overflow-tooltip />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag>{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="190" />
      <el-table-column label="操作" width="230" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.source_type === 'lead'" size="small" plain @click="markContacted(row)">已联系</el-button>
          <el-button size="small" type="primary" @click="openConvert(row)">转工单</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="convertVisible" title="转为工单" width="520px">
      <el-form label-width="100px">
        <el-form-item label="来源">
          <el-input :model-value="currentItemLabel" disabled />
        </el-form-item>
        <el-form-item label="客户 ID">
          <el-input v-model="convertForm.customer_id" :disabled="currentItem?.source_type === 'appointment'" placeholder="官网线索需填写已有客户 ID" />
        </el-form-item>
        <el-form-item label="车牌">
          <el-input v-model="convertForm.vehicle_plate" placeholder="例如：沪A12345" />
        </el-form-item>
        <el-form-item label="客户主诉">
          <el-input v-model="convertForm.description" type="textarea" :rows="4" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="convertVisible = false">取消</el-button>
        <el-button type="primary" :loading="converting" @click="submitConvert">创建工单</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../utils/request'

const router = useRouter()
const items = ref([])
const loading = ref(false)
const converting = ref(false)
const convertVisible = ref(false)
const currentItem = ref(null)
const convertForm = reactive({
  customer_id: '',
  vehicle_plate: '',
  description: '',
})

const statusLabel = (status) => ({
  new: '新线索',
  contacted: '已联系',
  draft: '预约草稿',
  submitted: '已提交',
  converted: '已转工单',
  closed: '已关闭',
}[status] || status || '-')

const currentItemLabel = computed(() => {
  if (!currentItem.value) return ''
  return `${currentItem.value.source_type === 'lead' ? '官网线索' : '小程序预约'} #${currentItem.value.id} · ${currentItem.value.title || ''}`
})

const loadInbox = async () => {
  loading.value = true
  try {
    items.value = await request.get('/mp/trial/inbox') || []
  } finally {
    loading.value = false
  }
}

const markContacted = async (row) => {
  await request.put(`/mp/leads/${row.id}`, { status: 'contacted' })
  ElMessage.success('已标记为已联系')
  await loadInbox()
}

const openConvert = (row) => {
  currentItem.value = row
  convertForm.customer_id = row.source_type === 'appointment' ? String(row.contact || '') : ''
  convertForm.vehicle_plate = row.vehicle_plate || ''
  convertForm.description = [row.title, row.message].filter(Boolean).join('；')
  convertVisible.value = true
}

const submitConvert = async () => {
  if (!currentItem.value) return
  if (!convertForm.customer_id || !convertForm.vehicle_plate || !convertForm.description) {
    ElMessage.warning('请补齐客户 ID、车牌和客户主诉')
    return
  }
  converting.value = true
  try {
    const result = await request.post('/mp/trial/workorders', {
      source_type: currentItem.value.source_type,
      source_id: currentItem.value.id,
      customer_id: convertForm.customer_id,
      vehicle_plate: convertForm.vehicle_plate,
      description: convertForm.description,
    })
    ElMessage.success('工单已创建')
    convertVisible.value = false
    await loadInbox()
    if (result?.id) {
      router.push({ name: 'orders', query: { order_id: result.id } })
    }
  } finally {
    converting.value = false
  }
}

onMounted(loadInbox)
</script>

<style scoped>
.trial-inbox {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.page-head h2 {
  margin: 0 0 6px;
  color: #172033;
}

.page-head p {
  margin: 0;
  color: #68758a;
}

.page-tip {
  border-radius: 8px;
}
</style>
