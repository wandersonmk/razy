<template>
  <ClientOnly>
    <font-awesome-icon 
      :icon="icon" 
      :class="className"
    />
    <template #fallback>
      <span :class="className">{{ fallback }}</span>
    </template>
  </ClientOnly>
</template>

<script setup lang="ts">
type IconTuple = [string, string]

defineProps<{
  icon: string | IconTuple
  className?: string
  fallback?: string
}>()
</script>

