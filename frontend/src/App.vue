<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router';
import { computed, onMounted, onUnmounted, ref } from 'vue';
import StatusPill from './components/StatusPill.vue';
import { useSnapshot } from './composables/useSnapshot';

const apiOnline = ref<boolean | null>(null);
let pingTimer: number | undefined;

async function pingHealth() {
  try {
    const res = await fetch('/api/health');
    apiOnline.value = res.ok;
  } catch {
    apiOnline.value = false;
  }
}

const snap = useSnapshot();
const state = computed(() => snap.snapshot.value.gcode_state ?? 'IDLE');

onMounted(() => {
  pingHealth();
  pingTimer = window.setInterval(pingHealth, 10_000);
});

onUnmounted(() => {
  if (pingTimer) window.clearInterval(pingTimer);
  snap.release();
});

const nav = [
  { to: '/', label: 'Overview' },
  { to: '/events', label: 'Events' },
  { to: '/camera', label: 'Camera' },
  { to: '/detector', label: 'Detector' },
];
</script>

<template>
  <div class="min-h-screen flex flex-col pb-20 md:pb-0">
    <header class="border-b border-line bg-bg-panel/70 backdrop-blur sticky top-0 z-20">
      <div class="max-w-6xl mx-auto px-5 py-3 flex items-center justify-between gap-4">
        <div class="flex items-center gap-3 min-w-0">
          <span class="text-2xl">🍝</span>
          <div class="leading-tight">
            <div class="font-mono text-sm tracking-wider">spaghetti monster</div>
            <div class="text-[10px] uppercase tracking-[0.18em] text-text-muted">Bambu A1</div>
          </div>
        </div>

        <nav class="hidden md:flex items-center gap-1">
          <RouterLink
            v-for="item in nav"
            :key="item.to"
            :to="item.to"
            class="nav-link"
            active-class="nav-link-active"
          >
            {{ item.label }}
          </RouterLink>
        </nav>

        <div class="flex items-center gap-3">
          <StatusPill :state="state" />
          <span class="flex items-center gap-1.5 font-mono text-[11px] text-text-muted">
            <span
              class="inline-block w-2 h-2 rounded-full"
              :class="apiOnline === null ? 'bg-state-idle' : apiOnline ? 'bg-brand' : 'bg-state-fail'"
            ></span>
            {{ apiOnline === null ? '…' : apiOnline ? 'api' : 'offline' }}
          </span>
        </div>
      </div>
    </header>

    <main class="flex-1 max-w-6xl w-full mx-auto px-5 py-6">
      <RouterView />
    </main>

    <!-- Mobile bottom nav -->
    <nav
      class="md:hidden fixed inset-x-0 bottom-0 z-20 border-t border-line bg-bg-panel/90 backdrop-blur"
    >
      <div class="max-w-6xl mx-auto grid grid-cols-4">
        <RouterLink
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="text-center py-2.5 text-xs font-mono text-text-muted"
          active-class="!text-brand"
        >
          {{ item.label }}
        </RouterLink>
      </div>
    </nav>
  </div>
</template>
