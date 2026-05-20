<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{ kind: string }>();

const map: Record<string, string> = {
  print_start: 'text-state-finish ring-state-finish/40 bg-state-finish/10',
  print_resume: 'text-state-finish ring-state-finish/40 bg-state-finish/10',
  print_pause: 'text-state-pause ring-state-pause/40 bg-state-pause/10',
  print_finish: 'text-state-running ring-state-running/40 bg-state-running/10',
  print_fail: 'text-state-fail ring-state-fail/40 bg-state-fail/10',
  print_error: 'text-state-fail ring-state-fail/40 bg-state-fail/10',
  hms: 'text-hms ring-hms/40 bg-hms/10',
  spaghetti_detected: 'text-spaghetti ring-spaghetti/40 bg-spaghetti/10',
};

const cls = computed(() => map[props.kind] ?? 'text-text-muted ring-line bg-bg-tile');
</script>

<template>
  <span class="pill" :class="cls">{{ kind }}</span>
</template>
