<template>
  <main>
    <section class="page-hero compact-hero">
      <p class="eyebrow">Contact</p>
      <h1>从下一次维修，或者下一次门店升级开始。</h1>
      <p>车主咨询、门店演示、合作沟通，请留下联系方式和需求。</p>
    </section>

    <section class="contact-layout">
      <div class="contact-copy">
        <h2>联系机车博士</h2>
        <p>告诉我们你是车主还是门店，以及你想解决的问题。我们会围绕你的场景继续完善服务路径。</p>
        <div class="contact-lines">
          <span>车主咨询</span>
          <span>门店演示预约</span>
          <span>SaaS 合作沟通</span>
        </div>
      </div>

      <form class="demo-form" @submit.prevent="submitLead">
        <label>
          <span>姓名</span>
          <input v-model="form.name" type="text" placeholder="你的称呼" autocomplete="name" required maxlength="80" />
        </label>
        <label>
          <span>联系方式</span>
          <input v-model="form.contact" type="text" placeholder="微信或手机号" required maxlength="120" />
        </label>
        <label>
          <span>身份</span>
          <select v-model="form.identity">
            <option>车主</option>
            <option>门店</option>
            <option>合作方</option>
          </select>
        </label>
        <label>
          <span>想了解什么</span>
          <textarea v-model="form.message" rows="4" maxlength="255" :placeholder="form.identity === '门店' ? '门店名称、所在城市，以及希望解决的问题' : '车型、车辆问题，以及期望到店时间'"></textarea>
        </label>
        <button type="submit" :disabled="submitting">{{ submitting ? '提交中...' : '提交预约咨询' }}</button>
        <p class="form-note">提交后由门店联系确认，具体到店时间以门店安排为准。</p>
        <p v-if="submitted" class="form-note" role="status">已收到，我们会把这条需求转给门店处理。</p>
        <p v-if="error" class="form-note form-note--error" role="alert">{{ error }}</p>
      </form>
    </section>
  </main>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const submitted = ref(false)
const submitting = ref(false)
const error = ref('')
const form = reactive({
  name: '',
  contact: '',
  identity: '车主',
  message: '',
})

const apiBase = (import.meta.env.VITE_API_BASE || '/api').replace(/\/+$/, '')
const route = useRoute()
watch(() => route.query.type, (type) => {
  form.identity = type === 'workshop' ? '门店' : '车主'
}, { immediate: true })

async function submitLead() {
  if (submitting.value) return
  error.value = ''
  submitted.value = false
  const payload = {
    name: String(form.name || '').trim(),
    contact: String(form.contact || '').trim(),
    identity: form.identity,
    message: String(form.message || '').trim(),
    source_page: typeof window !== 'undefined' ? window.location.href : '/contact',
    store_id: 'default',
  }
  if (!payload.name || !payload.contact) {
    error.value = '请留下姓名和联系方式。'
    return
  }
  submitting.value = true
  try {
    const response = await fetch(`${apiBase}/mp/leads`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    if (!response.ok) {
      throw new Error('submit failed')
    }
    submitted.value = true
    form.name = ''
    form.contact = ''
    form.identity = '车主'
    form.message = ''
  } catch {
    error.value = '提交失败，请稍后重试。已填写的内容会保留。'
  } finally {
    submitting.value = false
  }
}
</script>
