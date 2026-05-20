<script setup lang="ts">
import { computed, onUnmounted } from 'vue';
import CameraTile from '../components/CameraTile.vue';
import { useSnapshot } from '../composables/useSnapshot';

const snap = useSnapshot();
const stateLabel = computed(() => snap.snapshot.value.gcode_state ?? 'IDLE');

onUnmounted(() => snap.release());
</script>

<template>
  <section class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="font-mono text-xl">Camera</h2>
      <span class="text-[11px] text-text-muted font-mono">refreshes every 5s</span>
    </div>

    <CameraTile :overlay-state="stateLabel" :interval-ms="5000" />

    <p class="text-xs text-text-muted font-mono">
      Frame updates only while AI detector is enabled and a print is RUNNING.
    </p>
  </section>
</template>
