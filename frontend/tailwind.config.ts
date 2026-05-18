import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#F7F6F3",
        rim: "#E4E2DC",
        ink: {
          DEFAULT: "#1A1A18",
          muted: "#6B6860",
          subtle: "#A09D98",
        },
        accent: {
          DEFAULT: "#2D6A4F",
          hover: "#245C43",
          light: "#EAF2EE",
        },
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
