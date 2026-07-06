/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Nutanix brand palette.
        iris: {
          DEFAULT: "#7855FA", // Iris Purple (primary)
          light: "#9B82FF",
          dark: "#5B3FD0",
        },
        charcoal: {
          DEFAULT: "#131313",
          light: "#1E1E22",
          card: "#26262C",
          border: "#35353D",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 24px rgba(120, 85, 250, 0.35)",
      },
    },
  },
  plugins: [],
};
