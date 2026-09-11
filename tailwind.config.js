/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html", "./static/js/**/*.js"],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Space Grotesk"', "sans-serif"], // Titres
        body: ['"IBM Plex Sans"', "sans-serif"], // Texte principal
        mono: ['"IBM Plex Mono"', "monospace"], // Code/mono
      },
      colors: {
        // Palette sombre principale
        slate: {
          50: "#F8FAFC",
          100: "#F1F5F9",
          500: "#64748B",
          600: "#475569",
          700: "#334155",
          800: "#1E293B",
          900: "#0F172A", // Fond principal sombre
          950: "#020617", // Option pour un fond encore plus sombre
        },
        // Vert émeraude pour CTA et disponibilité
        emerald: {
          50: "#ECFDF5",
          100: "#D1FAE5",
          500: "#10B981", // Vert émeraude (CTA principal)
          600: "#059669", // Survol CTA
          700: "#047857", // Texte/icônes CTA
        },
        // Couleurs neutres pour textes et fonds secondaires
        neutral: {
          50: "#F8FAFC", // Texte principal (blanc cassé)
          100: "#F1F5F9",
          300: "#D1D5DB",
          400: "#9CA3AF",
          500: "#6B7280",
          600: "#4B5563",
          700: "#374151",
          900: "#111827",
        },
        // Couleurs pour les statuts (succès, avertissement, erreur, info)
        success: {
          50: "#ECFDF5",
          100: "#D1FAE5",
          500: "#10B981", // Identique à emerald-500 pour cohérence
          600: "#059669",
          700: "#047857",
        },
        warning: {
          50: "#FFFBEB",
          100: "#FEF3C7",
          500: "#F59E0B", // Orange pour avertissements
          600: "#D97706",
          700: "#B45309",
        },
        error: {
          50: "#FEF2F2",
          100: "#FEE2E2",
          500: "#EF4444", // Rouge pour erreurs
          600: "#DC2626",
          700: "#B91C1C",
        },
        info: {
          50: "#EFF6FF",
          100: "#DBEAFE",
          500: "#3B82F6", // Bleu pour informations
          600: "#2563EB",
          700: "#1D4ED8",
        },
      },
      borderRadius: {
        xl: "0.75rem",
        "2xl": "1rem",
      },
      boxShadow: {
        card: "0 1px 3px 0 rgb(0 0 0 / 0.08), 0 1px 2px -1px rgb(0 0 0 / 0.06)",
        "card-hover":
          "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.08)",
        elevated:
          "0 10px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.08)",
        nav: "0 2px 10px 0 rgb(0 0 0 / 0.2)",
        // Ombre pour les CTA en vert émeraude
        "emerald-glow": "0 0 20px -5px rgba(16, 185, 129, 0.3)",
      },
      animation: {
        "fade-in": "fadeIn 0.3s ease-in-out",
        "slide-up": "slideUp 0.3s ease-out",
        "slide-down": "slideDown 0.3s ease-out",
        "slide-right": "slideRight 0.3s ease-out",
        "scale-in": "scaleIn 0.2s ease-out",
        "pulse-soft": "pulseSoft 2s ease-in-out infinite",
        glow: "glow 2s ease-in-out infinite alternate", // Animation pour l'effet lumineux des CTA
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { transform: "translateY(12px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        slideDown: {
          "0%": { transform: "translateY(-12px)", opacity: "0" },
          "100%": { transform: "translateY(0)", opacity: "1" },
        },
        slideRight: {
          "0%": { transform: "translateX(-12px)", opacity: "0" },
          "100%": { transform: "translateX(0)", opacity: "1" },
        },
        scaleIn: {
          "0%": { transform: "scale(0.95)", opacity: "0" },
          "100%": { transform: "scale(1)", opacity: "1" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.7" },
        },
        glow: {
          "0%": { boxShadow: "0 0 20px -5px rgba(16, 185, 129, 0.3)" },
          "100%": { boxShadow: "0 0 30px -5px rgba(16, 185, 129, 0.5)" },
        },
      },
    },
  },
  plugins: [],
};
