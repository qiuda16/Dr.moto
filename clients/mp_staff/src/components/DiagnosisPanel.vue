<template>
  <div class="diagnosis-panel">
    <van-cell-group title="Diagnosis Result">
      <van-field
        v-model="diagnosis.codes"
        label="Fault Codes"
        placeholder="e.g. P0300"
        right-icon="scan"
      />
      <van-field
        v-model="diagnosis.conclusion"
        label="Conclusion"
        type="textarea"
        rows="3"
        placeholder="Technician's conclusion..."
      />
      <van-field
        v-model="diagnosis.advice"
        label="Advice"
        type="textarea"
        rows="2"
        placeholder="Repair recommendations..."
      />
    </van-cell-group>

    <van-cell-group title="Evidence (Photo/Video)">
      <div class="evidence-grid">
        <van-uploader v-model="fileList" multiple :max-count="4" :after-read="afterRead" />
      </div>
    </van-cell-group>

    <div class="actions">
      <van-button block type="primary" @click="saveDiagnosis">Save Diagnosis</van-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { showToast } from 'vant'
import request from '../utils/request'

const props = defineProps(['orderId'])
const emit = defineEmits(['saved'])

const diagnosis = reactive({
  codes: '',
  conclusion: '',
  advice: ''
})

const fileList = ref([])

const afterRead = async (file) => {
  file.status = 'uploading'
  file.message = 'Uploading...'
  
  try {
    const formData = new FormData()
    formData.append('file', file.file)
    
    // Call BFF Upload
    const res = await request.post(`/mp/workorders/${props.orderId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    
    file.status = 'done'
    file.message = 'Done'
    file.url = res.url // Save URL for submission
  } catch (err) {
    file.status = 'failed'
    file.message = 'Failed'
  }
}

const saveDiagnosis = async () => {
  if (!diagnosis.conclusion) return showToast('Conclusion required')
  
  // Submit to BFF
  // In real app: POST /mp/workorders/{id}/diagnosis
  showToast('Diagnosis Saved')
  emit('saved')
}
</script>

<style scoped>
.diagnosis-panel { padding: 10px; background: #f7f8fa; }
.evidence-grid { padding: 10px 16px; background: white; }
.actions { padding: 20px 16px; }
</style>
