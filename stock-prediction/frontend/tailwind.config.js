/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "sans-serif"]
      },
      colors: {
        ink: "#111111",
        muted: "#6B7280",
        accent: "#007AFF",
        surface: "#FFFFFF",
        soft: "#FAFAFA",
        border: "#E5E7EB"
      },
      boxShadow: {
        soft: "0 1px 2px rgba(0,0,0,0.04)",
        hover: "0 6px 20px rgba(17, 24, 39, 0.06)"
      }
    }
  },
  plugins: []
};
