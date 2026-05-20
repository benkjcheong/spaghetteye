/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts,js}'],
  theme: {
    extend: {
      colors: {
        bg: {
          deep: '#0e1116',
          panel: '#171b22',
          tile: '#1f242d',
        },
        line: '#2a313c',
        text: {
          primary: '#f3f4f6',
          muted: '#8a93a3',
        },
        brand: {
          DEFAULT: '#00ae42',
          soft: '#00ae4226',
        },
        state: {
          running: '#00ae42',
          pause: '#f59e0b',
          finish: '#3b82f6',
          fail: '#ef4444',
          idle: '#6b7280',
        },
        hms: '#f59e0b',
        spaghetti: '#d946ef',
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        tile: '0 1px 0 0 rgba(255,255,255,0.04) inset, 0 8px 24px -8px rgba(0,0,0,0.6)',
      },
      backgroundImage: {
        grid: 'linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)',
      },
      backgroundSize: {
        grid: '32px 32px',
      },
    },
  },
  plugins: [],
};
