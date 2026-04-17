<template>
  <div class="settings-page">
    <div class="card settings-head">
      <div>
        <h2>门店设置</h2>
        <p>这里只管理高频默认值，不改变系统布局。保存后，工单中心、主数据中心和壳层标题会自动使用新设置。</p>
      </div>
      <div class="head-actions">
        <el-button @click="loadSettings">刷新</el-button>
        <el-button type="primary" :loading="saving" @click="saveSettings">保存设置</el-button>
      </div>
    </div>

    <div class="settings-grid">
      <div class="card">
        <div class="section-title">门店信息</div>
        <el-form :model="form" label-width="110px">
          <el-form-item label="店名">
            <el-input v-model="form.store_name" maxlength="120" show-word-limit />
          </el-form-item>
          <el-form-item label="品牌名">
            <el-input v-model="form.brand_name" maxlength="80" show-word-limit />
          </el-form-item>
          <el-form-item label="角标文字">
            <el-input v-model="form.sidebar_badge_text" maxlength="40" show-word-limit />
          </el-form-item>
          <el-form-item label="主色">
            <div class="color-row">
              <el-input v-model="form.primary_color" maxlength="32" />
              <span class="color-preview" :style="{ backgroundColor: form.primary_color || '#409EFF' }"></span>
            </div>
          </el-form-item>
        </el-form>
      </div>

      <div class="card">
        <div class="section-title">默认业务值</div>
        <el-form :model="form" label-width="110px">
          <el-form-item label="默认工时价">
            <el-input-number v-model="form.default_labor_price" :min="0" :precision="2" controls-position="right" style="width: 100%" />
          </el-form-item>
          <el-form-item label="默认交车备注">
            <el-input v-model="form.default_delivery_note" type="textarea" :rows="4" maxlength="255" show-word-limit />
          </el-form-item>
        </el-form>
      </div>
    </div>

    <div class="card">
      <div class="section-title">常用主诉短语</div>
      <div class="phrase-tip">快速接车里的快捷短语会优先使用这里的内容。每行一条，最多 12 条。</div>
      <el-input
        v-model="phrasesText"
        type="textarea"
        :rows="8"
        maxlength="1600"
        show-word-limit
        placeholder="例如：&#10;常规保养，检查机油与机滤&#10;前刹车异响，顺便做安全检查"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'

import request from '../utils/request'
import { applyAppSettings, createAppSettingsState, dispatchAppSettingsChanged } from '../composables/appSettings'

const saving = ref(false)
const phrasesText = ref('')
const form = reactive(createAppSettingsState())

const normalizePhraseList = () =>
  String(phrasesText.value || '')
    .split(/\r?\n/)
    .map((item) => String(item || '').trim())
    .filter(Boolean)
    .slice(0, 12)

const loadSettings = async () => {
  try {
    const data = await request.get('/mp/settings')
    applyAppSettings(form, data)
    phrasesText.value = Array.isArray(data?.common_complaint_phrases) ? data.common_complaint_phrases.join('\n') : ''
  } catch {
    applyAppSettings(form)
    phrasesText.value = ''
    ElMessage.error('门店设置加载失败，请稍后重试')
  }
}

const saveSettings = async () => {
  saving.value = true
  try {
    await request.put('/mp/settings', {
      ...form,
      common_complaint_phrases: normalizePhraseList(),
    })
    dispatchAppSettingsChanged()
    ElMessage.success('门店设置已保存')
  } catch (error) {
    ElMessage.error(error?.message || '门店设置保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.settings-page {
  display: grid;
  gap: 16px;
}
.settings-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}
.settings-head h2 {
  margin: 0 0 8px;
  font-size: 24px;
  color: #162033;
}
.settings-head p {
  margin: 0;
  color: #6f7b91;
  line-height: 1.7;
}
.head-actions {
  display: flex;
  gap: 10px;
}
.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.section-title {
  margin-bottom: 14px;
  font-size: 16px;
  font-weight: 700;
  color: #162033;
}
.phrase-tip {
  margin-bottom: 12px;
  color: #7a8599;
  font-size: 13px;
  line-height: 1.7;
}
.color-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.color-preview {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid #dbe3ee;
  flex: 0 0 auto;
}
@media (max-width: 960px) {
  .settings-head,
  .settings-grid {
    grid-template-columns: 1fr;
    display: grid;
  }
  .head-actions {
    justify-content: flex-start;
  }
}
</style>
