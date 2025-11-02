import { applyTheme } from '../utils/themes.js';

/**
 * ThemeToggle - Button to toggle between light and dark themes
 *
 * @param {Object} props
 * @param {string} props.currentTheme - Current theme ID ('dark' or 'light')
 * @param {Function} props.onToggle - Callback when theme is toggled
 */
export default function ThemeToggle({ currentTheme, onToggle }) {
  const isDark = currentTheme === 'dark';

  const handleToggle = () => {
    const newTheme = isDark ? 'light' : 'dark';
    applyTheme(newTheme);
    onToggle(newTheme);
  };

  return (
    <button
      onClick={handleToggle}
      className="theme-toggle-button"
      title={`Switch to ${isDark ? 'light' : 'dark'} mode`}
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
    >
      {isDark ? (
        // Sun icon for light mode
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <circle cx="10" cy="10" r="3" stroke="currentColor" strokeWidth="1.5" />
          <line x1="10" y1="2" x2="10" y2="4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <line x1="10" y1="16" x2="10" y2="18" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <line x1="18" y1="10" x2="16" y2="10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <line x1="4" y1="10" x2="2" y2="10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <line x1="15.5" y1="4.5" x2="14" y2="6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <line x1="6" y1="14" x2="4.5" y2="15.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <line x1="15.5" y1="15.5" x2="14" y2="14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <line x1="6" y1="6" x2="4.5" y2="4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      ) : (
        // Moon icon for dark mode
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <path
            d="M17 10.5A7 7 0 1 1 9.5 3a5.5 5.5 0 0 0 7.5 7.5Z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )}
    </button>
  );
}
