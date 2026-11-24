/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // High contrast colors meeting WCAG 2.1 AA (>= 4.5:1 text, >= 3:1 controls)
        brand: {
          50: '#f0f7ff',
          100: '#e0effe',
          600: '#0052cc', // accessible high-contrast blue (5.2:1 against white)
          700: '#0043a8',
          800: '#003585',
          900: '#00255c',
        },
        danger: {
          700: '#b91c1c', // accessible red
          800: '#991b1b',
        },
        success: {
          700: '#15803d', // accessible green
          800: '#166534',
        }
      }
    },
  },
  plugins: [],
}
