<script setup lang="ts">
import { computed, onUnmounted } from 'vue';
import EventBadge from '../components/EventBadge.vue';
import LiveDot from '../components/LiveDot.vue';
import { useEventStream } from '../composables/useEventStream';

const stream = useEventStream();
const { events, streaming, error, newestSinceMount } = stream;

onUnmounted(() => stream.release());

function fmtTs(ts: number) {
  return new Date(ts * 1000).toLocaleString();
}

function dayKey(ts: number) {
  return new Date(ts * 1000).toDateString();
}

const grouped = computed(() => {
  const out: { day: string; items: typeof events.value }[] = [];
  for (const ev of events.value) {
    const day = dayKey(ev.ts);
    const last = out[out.length - 1];
    if (last && last.day === day) last.items.push(ev);
    else out.push({ day, items: [ev] });
  }
  return out;
});
</script>

<template>
  <section class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="font-mono text-xl">Events</h2>
      <LiveDot :live="streaming" />
    </div>

    <div v-if="error" class="tile-tight bg-state-fail/10 ring-state-fail/30 text-state-fail text-sm font-mono">
      {{ error }}
    </div>

    <div v-if="!events.length" class="text-text-muted text-sm font-mono">
      No events yet. They appear here as the printer state changes.
    </div>

    <div v-for="group in grouped" :key="group.day" class="space-y-2">
      <div class="text-[11px] uppercase tracking-wider text-text-muted font-mono pt-2">
        {{ group.day }}
      </div>
      <ul class="space-y-2">
        <li
          v-for="ev in group.items"
          :key="`${ev.ts}-${ev.kind}-${ev.title}`"
          class="tile-tight"
          :class="{ 'ring-brand/40 shadow-[0_0_0_1px_rgba(0,174,66,0.25)]': newestSinceMount === ev.ts }"
        >
          <div class="flex items-center justify-between gap-3">
            <EventBadge :kind="ev.kind" />
            <span class="text-[11px] text-text-muted font-mono">{{ fmtTs(ev.ts) }}</span>
          </div>
          <div class="mt-2 text-sm">{{ ev.title }}</div>
          <div v-if="ev.detail" class="text-xs text-text-muted mt-1 font-mono">{{ ev.detail }}</div>
          <div v-if="ev.file" class="text-xs text-text-muted/80 mt-1 font-mono truncate">
            file: {{ ev.file }}
          </div>
          <div
            v-if="ev.layer !== null && ev.layer_total !== null"
            class="text-xs text-text-muted/80 font-mono"
          >
            layer {{ ev.layer }} / {{ ev.layer_total }}
            <span v-if="ev.percent !== null">({{ ev.percent }}%)</span>
          </div>
          <div v-if="ev.hms_code" class="text-xs text-hms font-mono">HMS: {{ ev.hms_code }}</div>
        </li>
      </ul>
    </div>
  </section>
</template>
