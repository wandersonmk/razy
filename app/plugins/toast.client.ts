import Toast from "vue-toastification"
import "vue-toastification/dist/index.css"

export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.use(Toast, {
    position: 'top-right',
    timeout: 4000,
    closeOnClick: true,
    pauseOnFocusLoss: true,
    pauseOnHover: true,
    draggable: true,
    draggablePercent: 0.6,
    showCloseButtonOnHover: false,
    hideProgressBar: false,
    closeButton: "button",
    icon: true,
    rtl: false,
    transition: "Vue-Toastification__bounce",
    maxToasts: 5,
    newestOnTop: true
  })
  // Injetar a instância global exposta pelo plugin ($toast)
  const globalToast = (nuxtApp.vueApp.config.globalProperties as any)?.$toast
  if (globalToast) {
    nuxtApp.provide('toast', globalToast)
  }
})
