/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0f1420",
        panel: "#171e2e",
        panel2: "#1e2740",
        line: "#2a3552",
        text: "#e8ecf5",
        muted: "#93a0bb",
        green: "#1db954",
        red: "#f23645",
        accent: "#f5b942",
      },
      fontFamily: {
        sans: ["PingFang SC", "Microsoft YaHei", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
