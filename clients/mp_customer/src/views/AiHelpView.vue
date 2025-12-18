<template>
  <div class="page-container chat-view">
    <van-nav-bar
      title="DrMoto AI"
      left-arrow
      @click-left="$router.back()"
      fixed
      placeholder
    />

    <div class="chat-list" ref="chatList">
      <div v-for="(msg, i) in messages" :key="i" class="msg-row" :class="{ mine: msg.isMe }">
        <div class="avatar" v-if="!msg.isMe">🤖</div>
        <div class="bubble">{{ msg.text }}</div>
        <div class="avatar" v-if="msg.isMe">👤</div>
      </div>
      <div v-if="typing" class="msg-row">
        <div class="avatar">🤖</div>
        <div class="bubble typing">...</div>
      </div>
    </div>

    <div class="input-area">
      <input v-model="inputText" placeholder="Ask about maintenance..." @keyup.enter="send" />
      <button @click="send">Send</button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const messages = ref([
  { text: 'Hello! I am DrMoto AI. How can I help with your vehicle today?', isMe: false }
])
const inputText = ref('')
const typing = ref(false)
const chatList = ref(null)

const scrollToBottom = () => {
  nextTick(() => {
    if (chatList.value) chatList.value.scrollTop = chatList.value.scrollHeight
  })
}

const send = () => {
  if (!inputText.value.trim()) return
  
  messages.value.push({ text: inputText.value, isMe: true })
  const query = inputText.value
  inputText.value = ''
  scrollToBottom()
  
  typing.value = true
  
  // Mock AI Response
  setTimeout(() => {
    let reply = "I recommend booking a checkup for that."
    if (query.includes('oil')) reply = "For Ninja 400, we recommend Motul 7100 10W40. Need an oil change?"
    if (query.includes('tire')) reply = "Check your tire pressure first (2.4 bar front, 2.6 bar rear)."
    
    typing.value = false
    messages.value.push({ text: reply, isMe: false })
    scrollToBottom()
  }, 1000)
}
</script>

<style scoped>
.chat-view { height: 100vh; display: flex; flex-direction: column; background: #f0f2f5; }
.chat-list { flex: 1; overflow-y: auto; padding: 20px; }

.msg-row { display: flex; align-items: flex-end; margin-bottom: 20px; gap: 10px; }
.msg-row.mine { justify-content: flex-end; }

.avatar { width: 36px; height: 36px; background: #ddd; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-size: 20px; }
.bubble { background: white; padding: 10px 15px; border-radius: 12px 12px 12px 0; max-width: 70%; box-shadow: 0 1px 2px rgba(0,0,0,0.1); }
.mine .bubble { background: #1989fa; color: white; border-radius: 12px 12px 0 12px; }

.input-area { padding: 10px; background: white; display: flex; gap: 10px; padding-bottom: max(10px, env(safe-area-inset-bottom)); }
.input-area input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 20px; outline: none; }
.input-area button { padding: 0 20px; background: #1989fa; color: white; border: none; border-radius: 20px; }
</style>
