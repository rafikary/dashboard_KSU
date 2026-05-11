import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

export function useAutoLogout(timeoutMinutes: number = 30) {
  const router = useRouter()
  const isActive = ref(true)
  let timeoutId: number | null = null

  const resetTimer = () => {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
    
    timeoutId = window.setTimeout(() => {
      handleLogout()
    }, timeoutMinutes * 60 * 1000)
  }

  const handleLogout = () => {
    // Clear session
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user')
    
    // Redirect to login
    router.push('/login')
  }

  const handleActivity = () => {
    isActive.value = true
    resetTimer()
  }

  onMounted(() => {
    // Reset timer on user activity
    window.addEventListener('mousedown', handleActivity)
    window.addEventListener('keydown', handleActivity)
    window.addEventListener('scroll', handleActivity)
    window.addEventListener('touchstart', handleActivity)
    
    // Start timer
    resetTimer()
  })

  onUnmounted(() => {
    // Cleanup
    window.removeEventListener('mousedown', handleActivity)
    window.removeEventListener('keydown', handleActivity)
    window.removeEventListener('scroll', handleActivity)
    window.removeEventListener('touchstart', handleActivity)
    
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
  })

  return {
    isActive,
    resetTimer,
    handleLogout,
  }
}