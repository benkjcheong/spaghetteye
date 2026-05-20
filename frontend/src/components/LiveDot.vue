<script setup lang="ts">
defineProps<{ live: boolean; label?: string }>();
</script>

<template>
  <span class="inline-flex items-center gap-1.5 font-mono text-[11px] text-text-muted">
    <span
      class="relative inline-flex w-2 h-2 rounded-full"
      :class="live ? 'bg-brand' : 'bg-state-idle'"
    >
      <span
        v-if="live"
        class="absolute inset-0 rounded-full bg-brand opacity-60 anim-pulse-soft"
      ></span>
    </span>
    {{ label ?? (live ? 'live' : 'offline') }}
  </span>
</template>
