import type { Config } from 'tailwindcss'

const config: Partial<Config> = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: 'rgb(var(--color-background) / <alpha-value>)',
        foreground: 'rgb(var(--color-foreground) / <alpha-value>)',

        primary: {
          DEFAULT: 'rgb(var(--color-primary) / <alpha-value>)',
          foreground: 'rgb(var(--color-primary-fg) / <alpha-value>)'
        },

        secondary: {
          DEFAULT: 'rgb(var(--color-secondary) / <alpha-value>)',
          foreground: 'rgb(var(--color-secondary-fg) / <alpha-value>)'
        },

        accent: {
          DEFAULT: 'rgb(var(--color-accent) / <alpha-value>)',
          foreground: 'rgb(var(--color-accent-fg) / <alpha-value>)'
        },

        muted: {
          DEFAULT: 'rgb(var(--color-muted) / <alpha-value>)',
          foreground: 'rgb(var(--color-muted-fg) / <alpha-value>)'
        },

        card: {
          DEFAULT: 'rgb(var(--color-card) / <alpha-value>)',
          foreground: 'rgb(var(--color-card-fg) / <alpha-value>)'
        },

        popover: {
          DEFAULT: 'rgb(var(--color-popover) / <alpha-value>)',
          foreground: 'rgb(var(--color-popover-fg) / <alpha-value>)'
        },

        destructive: {
          DEFAULT: 'rgb(var(--color-destructive) / <alpha-value>)',
          foreground: 'rgb(var(--color-destructive-fg) / <alpha-value>)'
        },
        destructiveSurface: 'rgb(var(--color-destructive-surface) / <alpha-value>)',

        border: 'rgb(var(--color-border) / <alpha-value>)',
        input:  'rgb(var(--color-input) / <alpha-value>)',
        ring:   'rgb(var(--color-ring) / <alpha-value>)',

        white: '#FFFFFF'
      }
    }
  }
}

export default config
