import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./hooks/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        card: "var(--card)",
        text: "var(--text)",
        accent: "var(--accent)",
        accent2: "var(--accent-2)",
        muted: "var(--muted)"
      },
      fontFamily: {
        title: ["var(--font-title)"],
        body: ["var(--font-body)"]
      },
      boxShadow: {
        neo: "0 14px 48px rgba(17, 11, 31, 0.22)"
      }
    }
  },
  plugins: []
};

export default config;
