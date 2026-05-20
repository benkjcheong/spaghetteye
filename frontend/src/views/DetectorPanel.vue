<script setup lang="ts">
import { computed, onUnmounted } from 'vue';
import ProgressRing from '../components/ProgressRing.vue';
import { useDetector } from '../composables/useDetector';

const det = useDetector();
const { status, history, error } = det;

onUnmounted(() => det.release());

const confidence = computed(() => Math.round((status.value?.last_confidence ?? 0) * 100));

function fmtTick(ts: number | null) {
  if (!ts) return '—';
  const ago = Math.max(0, Math.round(Date.now() / 1000 - ts));
  return `${ago}s ago`;
}

const sparkPath = computed(() => {
  const data = history.value;
  if (data.length < 2) return '';
  const w = 320;
  const h = 60;
  const xStep = w / (data.length - 1);
  return data
    .map((v, i) => {
      const y = h - Math.max(0, Math.min(1, v)) * h;
      return `${i === 0 ? 'M' : 'L'} ${(i * xStep).toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(' ');
});
</script>

<template>
  <section class="space-y-6">
    <div class="flex items-baseline justify-between">
      <h2 class="font-mono text-xl">Spaghetti Detector</h2>
      <span
        class="pill"
        :class="status?.enabled ? 'text-brand ring-brand/40 bg-brand-soft' : 'text-text-muted ring-line bg-bg-tile'"
      >
        {{ status?.enabled ? 'enabled' : 'disabled' }}
      </span>
    </div>

    <div v-if="error" class="tile-tight bg-state-fail/10 ring-state-fail/30 text-state-fail text-sm font-mono">
      {{ error }}
    </div>

    <div v-if="!status?.enabled" class="tile-pad text-sm text-text-muted">
      AI detection is off. Set <code class="font-mono text-text-primary">SPAGHETTI_AI_ENABLED=true</code>
      in the backend <code class="font-mono text-text-primary">.env</code> and restart.
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="tile-pad md:col-span-1 flex flex-col items-center justify-center gap-3">
        <ProgressRing
          :value="confidence"
          :size="180"
          :stroke="14"
          color="#d946ef"
          label="Last Confidence"
        />
      </div>

      <div class="tile-pad md:col-span-2 space-y-4">
        <div class="grid grid-cols-3 gap-4">
          <div>
            <div class="text-[11px] uppercase tracking-wider text-text-muted">Last Tick</div>
            <div class="font-mono text-2xl mt-1">{{ fmtTick(status?.last_tick_ts ?? null) }}</div>
          </div>
          <div>
            <div class="text-[11px] uppercase tracking-wider text-text-muted">Consec. Hits</div>
            <div class="font-mono text-2xl mt-1">{{ status?.consecutive_hits ?? 0 }}</div>
          </div>
          <div>
            <div class="text-[11px] uppercase tracking-wider text-text-muted">Alert</div>
            <span
              class="pill mt-1.5"
              :class="status?.alerted ? 'text-state-fail ring-state-fail/40 bg-state-fail/10' : 'text-text-muted ring-line bg-bg-tile'"
            >
              {{ status?.alerted ? 'fired' : 'no' }}
            </span>
          </div>
        </div>

        <div>
          <div class="text-[11px] uppercase tracking-wider text-text-muted mb-2">Confidence (last {{ history.length }} ticks)</div>
          <svg viewBox="0 0 320 60" class="w-full h-16 bg-bg-tile/40 rounded ring-1 ring-line">
            <path :d="sparkPath" stroke="#d946ef" stroke-width="2" fill="none" />
          </svg>
        </div>

        <div>
          <div class="text-[11px] uppercase tracking-wider text-text-muted">Last Summary</div>
          <div class="font-mono text-sm text-text-primary/90 mt-1 break-words">
            {{ status?.last_summary ?? '—' }}
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
