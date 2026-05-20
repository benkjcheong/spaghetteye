<script setup lang="ts">
import { computed, onUnmounted } from 'vue';
import { RouterLink } from 'vue-router';
import StatusPill from '../components/StatusPill.vue';
import ProgressRing from '../components/ProgressRing.vue';
import EventBadge from '../components/EventBadge.vue';
import CameraTile from '../components/CameraTile.vue';
import { useSnapshot } from '../composables/useSnapshot';
import { useDetector } from '../composables/useDetector';
import { useEventStream } from '../composables/useEventStream';

const snap = useSnapshot();
const det = useDetector();
const evt = useEventStream();

onUnmounted(() => {
  snap.release();
  det.release();
  evt.release();
});

const { snapshot, lastUpdate, error } = snap;
const detector = det.status;
const events = evt.events;

const stateLabel = computed(() => snapshot.value.gcode_state ?? 'IDLE');
const percent = computed(() => Math.max(0, Math.min(100, snapshot.value.mc_percent ?? 0)));
const layer = computed(() => snapshot.value.layer_num ?? null);
const layerTotal = computed(() => snapshot.value.total_layer_num ?? null);
const file = computed(() => snapshot.value.subtask_name ?? null);
const nozzle = computed(() => snapshot.value.nozzle_temper ?? null);
const bed = computed(() => snapshot.value.bed_temper ?? null);

const remaining = computed(() => {
  const m = snapshot.value.mc_remaining_time;
  if (!m || m <= 0) return '—';
  const h = Math.floor(m / 60);
  const mm = m % 60;
  return h ? `${h}h ${mm}m` : `${mm}m`;
});

const recent = computed(() => events.value.slice(0, 5));
const detectorConfidence = computed(() => Math.round((detector.value?.last_confidence ?? 0) * 100));
</script>

<template>
  <section class="space-y-6">
    <div class="flex items-end justify-between gap-4 flex-wrap">
      <div>
        <h2 class="font-mono text-xl">Overview</h2>
        <p class="text-text-muted text-sm">Bambu A1 print monitor</p>
      </div>
      <div class="flex items-center gap-3">
        <StatusPill :state="stateLabel" size="md" />
        <span class="text-xs text-text-muted font-mono">
          {{ lastUpdate ? `updated ${new Date(lastUpdate).toLocaleTimeString()}` : 'waiting…' }}
        </span>
      </div>
    </div>

    <div v-if="error" class="tile-tight bg-state-fail/10 ring-state-fail/30 text-state-fail text-sm font-mono">
      {{ error }}
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
      <div class="tile-pad lg:col-span-8 flex flex-col gap-4">
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <div class="text-xs uppercase tracking-wider text-text-muted">Now Printing</div>
            <div class="mt-1.5 font-mono text-lg truncate" :title="file ?? ''">
              {{ file ?? 'No active job' }}
            </div>
          </div>
          <StatusPill :state="stateLabel" />
        </div>

        <div class="grid grid-cols-3 gap-4">
          <div>
            <div class="text-[11px] uppercase tracking-wider text-text-muted">Progress</div>
            <div class="font-mono text-2xl mt-1">{{ percent }}<span class="text-text-muted text-base">%</span></div>
          </div>
          <div>
            <div class="text-[11px] uppercase tracking-wider text-text-muted">Layer</div>
            <div class="font-mono text-2xl mt-1">
              {{ layer ?? '—' }}<span class="text-text-muted text-base"> / {{ layerTotal ?? '—' }}</span>
            </div>
          </div>
          <div>
            <div class="text-[11px] uppercase tracking-wider text-text-muted">ETA</div>
            <div class="font-mono text-2xl mt-1">{{ remaining }}</div>
          </div>
        </div>

        <div class="h-2 rounded-full bg-bg-tile overflow-hidden">
          <div
            class="h-full bg-brand transition-[width] duration-700 ease-out"
            :style="{ width: `${percent}%` }"
          ></div>
        </div>
      </div>

      <div class="lg:col-span-4">
        <RouterLink to="/camera" class="block">
          <CameraTile :overlay-state="stateLabel" :show-refresh="false" />
        </RouterLink>
      </div>

      <div class="tile-pad lg:col-span-4 flex flex-col items-center justify-center gap-3">
        <ProgressRing :value="percent" :size="180" :stroke="14" label="Progress" />
      </div>

      <div class="tile-pad lg:col-span-4 flex flex-col gap-4 justify-center">
        <div class="text-[11px] uppercase tracking-wider text-text-muted">Temperatures</div>
        <div class="grid grid-cols-2 gap-4">
          <div class="flex flex-col items-center">
            <ProgressRing
              :value="nozzle ? Math.min(100, (nozzle / 300) * 100) : 0"
              :size="120"
              :stroke="10"
              color="#f59e0b"
              label="Nozzle"
            >
              <template #value>
                <span class="font-mono text-xl">{{ nozzle ?? '—' }}<span class="text-text-muted text-sm">°</span></span>
              </template>
            </ProgressRing>
          </div>
          <div class="flex flex-col items-center">
            <ProgressRing
              :value="bed ? Math.min(100, (bed / 110) * 100) : 0"
              :size="120"
              :stroke="10"
              color="#3b82f6"
              label="Bed"
            >
              <template #value>
                <span class="font-mono text-xl">{{ bed ?? '—' }}<span class="text-text-muted text-sm">°</span></span>
              </template>
            </ProgressRing>
          </div>
        </div>
      </div>

      <div class="tile-pad lg:col-span-4 flex flex-col gap-3">
        <div class="flex items-center justify-between">
          <div class="text-[11px] uppercase tracking-wider text-text-muted">AI Detector</div>
          <span
            class="pill text-[10px]"
            :class="detector?.enabled ? 'text-brand ring-brand/40 bg-brand-soft' : 'text-text-muted ring-line bg-bg-tile'"
          >
            {{ detector?.enabled ? 'enabled' : 'disabled' }}
          </span>
        </div>
        <div v-if="detector?.enabled" class="flex items-center justify-center">
          <ProgressRing
            :value="detectorConfidence"
            :size="140"
            :stroke="10"
            color="#d946ef"
            label="Confidence"
            :sublabel="`hits ${detector?.consecutive_hits ?? 0}`"
          />
        </div>
        <div v-else class="text-text-muted text-xs font-mono">
          Set <code class="text-text-primary">SPAGHETTI_AI_ENABLED=true</code> to enable.
        </div>
      </div>

      <div class="tile-pad lg:col-span-12">
        <div class="flex items-center justify-between mb-3">
          <div class="text-[11px] uppercase tracking-wider text-text-muted">Recent Events</div>
          <RouterLink to="/events" class="text-xs font-mono text-brand hover:underline">view all →</RouterLink>
        </div>
        <div v-if="!recent.length" class="text-text-muted text-sm font-mono">Quiet so far.</div>
        <ul v-else class="grid grid-cols-1 md:grid-cols-2 gap-2">
          <li
            v-for="ev in recent"
            :key="`${ev.ts}-${ev.kind}-${ev.title}`"
            class="bg-bg-tile/60 rounded-lg ring-1 ring-line px-3 py-2 flex items-start gap-3"
          >
            <EventBadge :kind="ev.kind" />
            <div class="min-w-0 flex-1">
              <div class="text-sm truncate">{{ ev.title }}</div>
              <div class="text-[11px] text-text-muted font-mono mt-0.5">
                {{ new Date(ev.ts * 1000).toLocaleTimeString() }}
                <span v-if="ev.file"> · {{ ev.file }}</span>
              </div>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
