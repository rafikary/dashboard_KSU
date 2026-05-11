<template>
  <div 
    :class="[
      'bg-gray-200 dark:bg-gray-700 animate-pulse', 
      type === 'circle' ? 'rounded-full' : 'rounded-md',
      widthClass, 
      heightClass
    ]"
  ></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  type?: 'box' | 'circle' | 'text'
  width?: string
  height?: string
}>(), {
  type: 'box',
  width: 'w-full',
  height: 'h-4'
})

const widthClass = computed(() => props.width)
const heightClass = computed(() => props.type === 'circle' ? props.height : props.height)
</script>