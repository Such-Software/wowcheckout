import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#1a1020",
        "ink-soft": "#2d1f3a",
        cream: "#fdf5f8",
        sand: "#fce8ef",
        clay: "#d63b7c",
        wownero: "#e8308c",
        sage: "#c9a832",
        fog: "rgba(26, 16, 32, 0.08)",
        card: "rgba(253, 245, 248, 0.88)",
        stroke: "rgba(26, 16, 32, 0.18)",
      },
      fontFamily: {
        sans: ["Space Grotesk", "Helvetica Neue", "Arial", "sans-serif"],
        serif: ["Crimson Pro", "Georgia", "serif"],
      },
      boxShadow: {
        soft: "0 18px 36px rgba(26, 16, 32, 0.08)",
        card: "0 24px 50px rgba(26, 16, 32, 0.12)",
        deep: "0 24px 60px rgba(26, 16, 32, 0.26)",
      },
      borderRadius: {
        xl: "1.2rem",
        "2xl": "1.6rem",
        "3xl": "1.8rem",
      },
    },
  },
  plugins: [],
};

export default config;
