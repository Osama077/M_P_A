/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef8ff',
          100: '#d7efff',
          200: '#b6e2ff',
          300: '#83ceff',
          400: '#48b2ff',
          500: '#1e90ff',
          600: '#0f70e6',
          700: '#1159bf',
          800: '#154a99',
          900: '#173f7a'
        },
        accent: {
          50: '#fff4ed',
          100: '#ffe6d4',
          200: '#ffc7a2',
          300: '#ffa06f',
          400: '#ff7a47',
          500: '#f45b2a',
          600: '#d84319',
          700: '#b43416',
          800: '#902d18',
          900: '#762818'
        }
      },
      boxShadow: {
        soft: '0 10px 30px rgba(15, 23, 42, 0.08)',
        glow: '0 10px 30px rgba(30, 144, 255, 0.25), 0 6px 18px rgba(244, 91, 42, 0.18)'
      }
    }
  },
  plugins: []
};
