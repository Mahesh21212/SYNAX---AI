/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './hooks/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#07080c',
          900: '#0b0d13',
          850: '#10131b',
          800: '#151922',
          700: '#1d2230',
          600: '#2a3040',
          500: '#3b4356',
        },
        accent: {
          50: '#eef4ff',
          100: '#dbe6ff',
          300: '#9db4ff',
          400: '#7d97ff',
          500: '#5b7cfa',
          600: '#4462e0',
          700: '#3550bd',
        },
        signal: {
          ok: '#34d399',
          warn: '#fbbf24',
          err: '#f87171',
        },
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '0.35' },
          '50%': { opacity: '1' },
        },
      },
      animation: {
        'fade-up': 'fade-up 0.22s ease-out both',
        'pulse-soft': 'pulseSoft 1.4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};
