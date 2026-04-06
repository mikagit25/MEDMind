/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        syne: ["Syne", "sans-serif"],
        serif: ["Source Serif 4", "serif"],
      },
      colors: {
        ink: {
          DEFAULT: "#1a1814",
          2: "#4a453e",
          3: "#8a8278",
        },
        bg: {
          DEFAULT: "#f0ede8",
          2: "#e8e4de",
        },
        surface: {
          DEFAULT: "#ffffff",
          2: "#f7f4f0",
        },
        border: {
          DEFAULT: "#d8d2c8",
          2: "#c8c0b4",
        },
        red: {
          DEFAULT: "#c0392b",
          2: "#e74c3c",
          light: "#fdf0ef",
        },
        blue: {
          DEFAULT: "#1a4a7a",
          2: "#2980b9",
          light: "#eef4fb",
        },
        green: {
          DEFAULT: "#1a6a3a",
          2: "#27ae60",
          light: "#edfaf3",
        },
        amber: {
          DEFAULT: "#8a5a00",
          2: "#d4a030",
          light: "#fdf8ec",
        },
        gold: "#e8c97a",
      },
      animation: {
        "fade-up": "fadeUp 0.22s ease-out",
        blink: "blink 2s ease-in-out infinite",
        spin: "spin 0.7s linear infinite",
      },
      keyframes: {
        fadeUp: {
          from: { opacity: 0, transform: "translateY(7px)" },
          to: { opacity: 1, transform: "none" },
        },
        blink: {
          "0%, 100%": { opacity: 1 },
          "50%": { opacity: 0.3 },
        },
      },
    },
  },
  plugins: [],
};
