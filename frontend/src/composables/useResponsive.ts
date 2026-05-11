import { computed, onMounted, onUnmounted, ref } from 'vue'

export function useResponsive() {
  const width = ref(window.innerWidth)

  const onResize = () => {
    width.value = window.innerWidth
  }

  onMounted(() => window.addEventListener('resize', onResize))
  onUnmounted(() => window.removeEventListener('resize', onResize))

  const isMobile = computed(() => width.value < 768)
  const isTablet = computed(() => width.value >= 768 && width.value < 1200)
  const isDesktop = computed(() => width.value >= 1200)

  return { width, isMobile, isTablet, isDesktop }
}
