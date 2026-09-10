/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          primary: '#FFFFFF',
          secondary: '#F8F9FB',
          subtle: '#F1F3F5',
          sidebar: '#F8F9F9',
        },
        accent: {
          DEFAULT: '#2563EB',
          hover: '#1D4ED8',
          active: '#1E40AF',
          subtle: '#EFF6FF',
          dim: '#93C5FD',
        },
        success: {
          DEFAULT: '#059669',
          bg: '#ECFDF5',
        },
        error: {
          DEFAULT: '#DC2626',
          bg: '#FEF2F2',
        },
        content: {
          primary: '#111827',
          body: '#374151',
          secondary: '#6B7280',
          muted: '#9CA3AF',
          inverse: '#FFFFFF',
        },
        border: {
          DEFAULT: '#E5E7EB',
          hover: '#D1D5DB',
          subtle: '#F3F4F6',
        },
      },
      fontFamily: {
        sans: ['Inter', 'Noto Sans SC', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'Fira Code', 'monospace'],
        display: ['DM Serif Display', 'Noto Serif SC', 'serif'],
      },
    },
  },
  plugins: [],
};
