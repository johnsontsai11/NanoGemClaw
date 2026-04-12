/**
 * Simple console logger (replaces pino for simplicity)
 */

import { EventEmitter } from 'node:events';
import { TIMEZONE } from './config.js';
import { getLocalTimestamp } from './utils/time.js';

export interface LogEntry {
  id: number;
  timestamp: string;
  level: string;
  message: string;
  data?: unknown;
}

let currentLogLevel = process.env.LOG_LEVEL || 'info';

const levels: Record<string, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

const MAX_BUFFER_SIZE = 500;
const logBuffer: LogEntry[] = [];
let logIdCounter = 0;

export const logEmitter = new EventEmitter();

function shouldLog(level: string): boolean {
  return levels[level] >= levels[currentLogLevel];
}

const SENSITIVE_KEYS = /key|token|secret|password|credential|auth/i;

function maskSensitiveData(obj: unknown): unknown {
  if (typeof obj !== 'object' || obj === null) return obj;
  if (Array.isArray(obj)) return obj.map(maskSensitiveData);
  const masked: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    masked[k] =
      SENSITIVE_KEYS.test(k) && typeof v === 'string' ? '[REDACTED]' : v;
  }
  return masked;
}

function formatData(data: unknown): string {
  if (data === undefined || data === null) return '';
  if (typeof data === 'string') return data;
  if (typeof data === 'object') {
    const masked = maskSensitiveData(data);
    if (Object.keys(masked as object).length === 0) return '';
    return JSON.stringify(masked);
  }
  return String(data);
}

function addToBuffer(entry: LogEntry): void {
  const maskedEntry = { ...entry, data: maskSensitiveData(entry.data) };
  logBuffer.push(maskedEntry);
  if (logBuffer.length > MAX_BUFFER_SIZE) {
    logBuffer.shift();
  }
  logEmitter.emit('log', maskedEntry);
}

export function getLogBuffer(): LogEntry[] {
  return [...logBuffer];
}

export function setLogLevel(level: string): void {
  if (levels[level] !== undefined) {
    currentLogLevel = level;
  }
}

export const logger = {
  debug: (data: unknown, msg?: string) => {
    if (shouldLog('debug')) {
      const timestamp = getLocalTimestamp(TIMEZONE);
      const message = `[${timestamp}] [DEBUG] ${msg || ''} ${formatData(data)}`;
      console.log(message);
      addToBuffer({
        id: ++logIdCounter,
        timestamp,
        level: 'debug',
        message: `[DEBUG] ${msg || ''} ${formatData(data)}`,
        data,
      });
    }
  },
  info: (data: unknown, msg?: string) => {
    if (shouldLog('info')) {
      const timestamp = getLocalTimestamp(TIMEZONE);
      const message = `[${timestamp}] [INFO] ${msg || ''} ${formatData(data)}`;
      console.log(message);
      addToBuffer({
        id: ++logIdCounter,
        timestamp,
        level: 'info',
        message: `[INFO] ${msg || ''} ${formatData(data)}`,
        data,
      });
    }
  },
  warn: (data: unknown, msg?: string) => {
    if (shouldLog('warn')) {
      const timestamp = getLocalTimestamp(TIMEZONE);
      const message = `[${timestamp}] [WARN] ${msg || ''} ${formatData(data)}`;
      console.warn(message);
      addToBuffer({
        id: ++logIdCounter,
        timestamp,
        level: 'warn',
        message: `[WARN] ${msg || ''} ${formatData(data)}`,
        data,
      });
    }
  },
  error: (data: unknown, msg?: string) => {
    if (shouldLog('error')) {
      const timestamp = getLocalTimestamp(TIMEZONE);
      const message = `[${timestamp}] [ERROR] ${msg || ''} ${formatData(data)}`;
      console.error(message);
      addToBuffer({
        id: ++logIdCounter,
        timestamp,
        level: 'error',
        message: `[ERROR] ${msg || ''} ${formatData(data)}`,
        data,
      });
    }
  },
};
