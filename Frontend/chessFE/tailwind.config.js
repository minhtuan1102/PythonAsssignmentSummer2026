/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: '#0B0E14',
        surface: '#141822',
        elevated: '#1C212D',
        border: '#262B38',
        text: '#F4F6F8',
        muted: '#9AA3B2',
        accent: '#E8B959',
        success: '#3FBE73',
        danger: '#E5484D',
        warning: '#F2B84B',
        boardLight: '#E8E4DA',
        boardDark: '#3B4252',
      }
    },
  },
  plugins: [],
}

