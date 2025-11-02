/**
 * Theme Configuration
 *
 * Defines light and dark theme color palettes
 */

export const THEMES = {
  dark: {
    id: 'dark',
    name: 'Dark Mode',
    colors: {
      // Backgrounds
      'bg-primary': 'radial-gradient(circle at top, #1f2937 0%, #020617 65%, #01030a 100%)',
      'bg-secondary': 'rgba(15, 23, 42, 0.9)',
      'bg-tertiary': 'rgba(30, 41, 59, 0.85)',
      'bg-surface': 'rgba(255, 255, 255, 0.04)',
      'bg-surface-alt': 'rgba(226, 232, 240, 0.12)',
      'bg-card': 'linear-gradient(145deg, rgba(255, 255, 255, 0.12), rgba(30, 58, 138, 0.12))',

      // Text
      'text-primary': 'rgb(248, 250, 252)',
      'text-secondary': 'rgba(226, 232, 240, 0.85)',
      'text-tertiary': 'rgba(148, 163, 184, 0.8)',

      // Accents
      'accent-primary': 'rgb(59, 130, 246)',
      'accent-secondary': 'rgb(34, 197, 94)',
      'accent-danger': 'rgb(239, 68, 68)',
      'accent-warning': 'rgb(245, 158, 11)',

      // Buttons
      'button-primary': 'linear-gradient(135deg, rgb(59, 130, 246), rgb(37, 99, 235))',
      'button-primary-hover': 'linear-gradient(135deg, rgb(37, 99, 235), rgb(29, 78, 216))',
      'button-secondary': 'rgb(31, 41, 55)',
      'button-secondary-hover': 'rgb(55, 65, 81)',

      // Borders
      'border-primary': 'rgb(31, 41, 55)',
      'border-secondary': 'rgb(55, 65, 81)',
      'border-accent': 'rgb(59, 130, 246)',
    },
  },
  light: {
    id: 'light',
    name: 'Light Mode',
    colors: {
      // Backgrounds
      'bg-primary': 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
      'bg-secondary': 'rgba(255, 255, 255, 0.95)',
      'bg-tertiary': 'rgba(241, 245, 249, 0.9)',
      'bg-surface': 'rgba(15, 23, 42, 0.03)',
      'bg-surface-alt': 'rgba(51, 65, 85, 0.08)',
      'bg-card': 'linear-gradient(145deg, rgba(255, 255, 255, 0.95), rgba(241, 245, 249, 0.8))',

      // Text
      'text-primary': 'rgb(15, 23, 42)',
      'text-secondary': 'rgba(51, 65, 85, 0.9)',
      'text-tertiary': 'rgba(100, 116, 139, 0.85)',

      // Accents
      'accent-primary': 'rgb(37, 99, 235)',
      'accent-secondary': 'rgb(22, 163, 74)',
      'accent-danger': 'rgb(220, 38, 38)',
      'accent-warning': 'rgb(217, 119, 6)',

      // Buttons
      'button-primary': 'linear-gradient(135deg, rgb(37, 99, 235), rgb(29, 78, 216))',
      'button-primary-hover': 'linear-gradient(135deg, rgb(29, 78, 216), rgb(30, 64, 175))',
      'button-secondary': 'rgb(226, 232, 240)',
      'button-secondary-hover': 'rgb(203, 213, 225)',

      // Borders
      'border-primary': 'rgb(226, 232, 240)',
      'border-secondary': 'rgb(203, 213, 225)',
      'border-accent': 'rgb(37, 99, 235)',
    },
  },
};

/**
 * Apply theme to document root
 * @param {string} themeId - Theme ID ('dark' or 'light')
 */
export function applyTheme(themeId) {
  const theme = THEMES[themeId];
  if (!theme) return;

  const root = document.documentElement;

  // Apply all color variables
  Object.entries(theme.colors).forEach(([key, value]) => {
    root.style.setProperty(`--${key}`, value);
  });

  // Save preference to localStorage
  localStorage.setItem('theme-preference', themeId);
}

/**
 * Get saved theme preference
 * @returns {string} Theme ID ('dark' or 'light')
 */
export function getSavedTheme() {
  return localStorage.getItem('theme-preference') || 'dark';
}

/**
 * Initialize theme on app load
 */
export function initializeTheme() {
  const savedTheme = getSavedTheme();
  applyTheme(savedTheme);
  return savedTheme;
}
