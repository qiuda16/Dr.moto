import { ref } from 'vue'

export function createPageFeedbackState() {
  const pageError = ref('')

  const clearPageError = () => {
    pageError.value = ''
  }

  const setPageError = (fallbackText, error) => {
    pageError.value = String(error?.message || fallbackText || '加载失败，请稍后重试')
  }

  return {
    pageError,
    clearPageError,
    setPageError,
  }
}
