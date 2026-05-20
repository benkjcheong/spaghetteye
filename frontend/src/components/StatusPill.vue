<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{ state?: string | null; size?: 'sm' | 'md' }>();

const map: Record<string, { label: string; cls: string; dot: string }> = {
  RUNNING: { label: 'Printing', cls: 'text-state-running ring-state-running/40 bg-state-running/10', dot: 'bg-state-running' },
  PAUSE: { label: 'Paused', cls: 'text-state-pause ring-state-pause/40 bg-state-pause/10', dot: 'bg-state-pause' },
  PREPARE: { label: 'Preparing', cls: 'text-state-finish ring-state-finish/40 bg-state-finish/10', dot: 'bg-state-finish' },
  FINISH: { label: 'Finished', cls: 'text-state-finish ring-state-finish/40 bg-state-finish/10', dot: 'bg-state-finish' },
  FAILED: { label: 'Failed', cls: 'text-state-fail ring-state-fail/40 bg-state-fail/10', dot: 'bg-state-fail' },
  IDLE: { label: 'Idle', cls: 'text-text-muted ring-line bg-bg-tile', dot: 'bg-state-idle' },
};

const v = computed(() => {
  const key = (props.state ?? 'IDLE').toUpperCase();
  return map[key] ?? { label: key, cls: 'text-text-muted ring-line bg-bg-tile', dot: 'bg-state-idle' };
});

const sizeCls = computed(() =>
  props.size === 'md' ? 'px-3 py-1.5 text-sm' : 'px-2.5 py-1 text-xs',
);
</script>

<template>
  <span class="pill" :class="[v.cls, sizeCls]">
    <span class="inline-block w-1.5 h-1.5 rounded-full" :class="v.dot"></span>
    {{ v.label }}
  </span>
</template>
