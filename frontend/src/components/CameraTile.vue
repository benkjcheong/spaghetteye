<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { frameUrl } from '../api/client';

const props = withDefaults(
  defineProps<{
    intervalMs?: number;
    showRefresh?: boolean;
    overlayState?: string | null;
  }>(),
  { intervalMs: 5000, showRefresh: true, overlayState: null },
);

const src = ref(frameUrl());
const updatedAt = ref<number | null>(null);
const error = ref(false);
let timer: number | undefined;

function refresh() {
  src.value = frameUrl();
}

function onLoad() {
  updatedAt.value = Date.now();
  error.value = false;
}

function onError() {
  error.value = true;
}

function onFocus() {
  refresh();
}

onMounted(() => {
  timer = window.setInterval(refresh, props.intervalMs);
  window.addEventListener('focus', onFocus);
});

onUnmounted(() => {
  if (timer) window.clearInterval(timer);
  window.removeEventListener('focus', onFocus);
});
</script>

<template>
  <div class="relative tile overflow-hidden">
    <div class="aspect-video bg-bg-tile flex items-center justify-center">
      <div
        v-if="error"
        class="text-text-muted font-mono text-xs text-center px-6 py-10"
      >
        No frame yet. Detector must capture one
        (printer RUNNING + <code class="text-text-primary">SPAGHETTI_AI_ENABLED=true</code>).
      </div>
      <img
        v-else
        :src="src"
        alt="printer camera frame"
        class="w-full h-full object-cover"
        @load="onLoad"
        @error="onError"
      />
    </div>
    <div class="absolute inset-x-0 top-0 p-3 flex items-center justify-between">
      <div class="pill bg-black/60 ring-white/10 text-white">
        <span class="inline-block w-1.5 h-1.5 rounded-full bg-brand anim-pulse-soft"></span>
        liveview
      </div>
      <div v-if="overlayState" class="pill bg-black/60 ring-white/10 text-white">
        {{ overlayState }}
      </div>
    </div>
    <div class="absolute inset-x-0 bottom-0 p-3 flex items-center justify-between text-[11px] font-mono">
      <span class="text-white/70 bg-black/40 px-2 py-0.5 rounded">
        {{ updatedAt ? new Date(updatedAt).toLocaleTimeString() : 'waiting' }}
      </span>
      <button
        v-if="showRefresh"
        @click="refresh"
        class="bg-black/40 hover:bg-black/60 text-white/80 px-2 py-0.5 rounded"
      >
        refresh
      </button>
    </div>
  </div>
</template>
