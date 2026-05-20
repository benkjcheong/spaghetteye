<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(
  defineProps<{
    value: number; // 0..100
    size?: number;
    stroke?: number;
    color?: string;
    track?: string;
    label?: string;
    sublabel?: string;
  }>(),
  {
    size: 160,
    stroke: 12,
    color: '#00ae42',
    track: 'rgba(255,255,255,0.08)',
  },
);

const radius = computed(() => (props.size - props.stroke) / 2);
const circumference = computed(() => 2 * Math.PI * radius.value);
const clamped = computed(() => Math.max(0, Math.min(100, props.value || 0)));
const dashOffset = computed(() => circumference.value * (1 - clamped.value / 100));
</script>

<template>
  <div class="relative inline-flex items-center justify-center" :style="{ width: `${size}px`, height: `${size}px` }">
    <svg :width="size" :height="size" class="-rotate-90 absolute inset-0">
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="radius"
        :stroke="track"
        :stroke-width="stroke"
        fill="none"
      />
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="radius"
        :stroke="color"
        :stroke-width="stroke"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashOffset"
        stroke-linecap="round"
        fill="none"
        class="transition-[stroke-dashoffset] duration-500 ease-out"
      />
    </svg>
    <div class="relative z-10 text-center pointer-events-none select-none">
      <div class="font-mono text-2xl leading-none">
        <slot name="value">{{ Math.round(clamped) }}<span class="text-text-muted text-base">%</span></slot>
      </div>
      <div v-if="label" class="text-[10px] uppercase tracking-wider text-text-muted mt-1.5">{{ label }}</div>
      <div v-if="sublabel" class="text-[10px] text-text-muted/80 font-mono mt-0.5">{{ sublabel }}</div>
    </div>
  </div>
</template>
