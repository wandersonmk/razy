<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  variant?: 'primary' | 'secondary' | 'accent' | 'outline' | 'ghost' | 'destructive'
  size?: 'sm' | 'md' | 'lg'
  block?: boolean
  loading?: boolean
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
}>(), {
  variant: 'primary',
  size: 'md',
  block: false,
  loading: false,
  disabled: false,
  type: 'button'
})

const baseClasses = 'inline-flex items-center justify-center rounded-md transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:opacity-50 disabled:cursor-not-allowed'

const variantClasses = computed(() => {
  switch (props.variant) {
    case 'secondary':
      return 'bg-secondary text-secondary-foreground hover:opacity-90'
    case 'accent':
      return 'bg-accent text-accent-foreground hover:opacity-90'
    case 'outline':
      return 'border border-border bg-transparent text-foreground hover:bg-muted'
    case 'ghost':
      return 'bg-transparent text-foreground hover:bg-muted'
    case 'destructive':
      return 'bg-destructive text-destructive-foreground hover:opacity-90'
    case 'primary':
    default:
      return 'bg-primary text-primary-foreground hover:opacity-90'
  }
})

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'h-9 px-3 text-sm'
    case 'lg':
      return 'h-11 px-5 text-base'
    case 'md':
    default:
      return 'h-10 px-4 text-sm'
  }
})
</script>

<template>
  <button
    :type="props.type"
    :disabled="props.disabled || props.loading"
    :class="[
      baseClasses,
      variantClasses,
      sizeClasses,
      { 'w-full': props.block, 'cursor-wait': props.loading }
    ]"
  >
    <span
      v-if="props.loading"
      class="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
    />
    <slot />
    <span v-if="props.loading" class="sr-only">Carregando</span>
  </button>
  
</template>



