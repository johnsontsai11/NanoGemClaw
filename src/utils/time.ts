/**
 * Time and Date Utilities
 */

/**
 * Get a local timestamp string in 'YYYY-MM-DD HH:mm:ss' format.
 * Useful for log files and human-readable dates.
 */
export function getLocalTimestamp(timezone: string): string {
  return new Date().toLocaleString('sv-SE', { timeZone: timezone });
}

/**
 * Get a verbose time context string including both local and UTC time.
 * Designed for injection into agent system instructions.
 */
export function getFormattedTimeContext(timezone: string): string {
  const now = new Date();
  const localTime = now.toLocaleString('en-US', {
    timeZone: timezone,
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: 'numeric',
    minute: 'numeric',
    second: 'numeric',
    hour12: true,
  });
  const utcTime = now.toISOString().replace('T', ' ').slice(0, 19) + ' UTC';
  return `Current time: ${localTime} (${timezone})\nUTC time: ${utcTime}`;
}
