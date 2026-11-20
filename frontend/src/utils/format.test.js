import { describe, expect, it } from 'vitest';
import { SLOT_STATUS_META, formatDuration, todayIst } from './format.js';

describe('formatDuration', () => {
  it('shows minutes under one hour', () => {
    expect(formatDuration(45)).toBe('45 min');
  });

  it('shows hours and minutes', () => {
    expect(formatDuration(135.4)).toBe('2 h 15 min');
  });

  it('returns a dash for missing values (active sessions)', () => {
    expect(formatDuration(null)).toBe('—');
    expect(formatDuration(undefined)).toBe('—');
  });
});

describe('todayIst', () => {
  it('returns a YYYY-MM-DD string', () => {
    expect(todayIst()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});

describe('SLOT_STATUS_META', () => {
  it('covers every status the backend can return', () => {
    expect(Object.keys(SLOT_STATUS_META).sort()).toEqual(['Available', 'Inactive', 'Occupied', 'Reserved']);
  });
});
