/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#0f1118",
        card: "#151820",
        border: "#1f2535",
        accent: "#4f8ff7",
        green: "#2dd4a8",
        red: "#ff6b6b",
      },
    },
  },
  plugins: [],
};
