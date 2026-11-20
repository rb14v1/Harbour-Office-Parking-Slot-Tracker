import { describe, expect, it } from 'vitest';
import { istInputsToIso, isoToIstInputs } from './istTime.js';

describe('istInputsToIso', () => {
  it('adds the IST offset', () => {
    expect(istInputsToIso('2026-12-01', '09:30')).toBe('2026-12-01T09:30:00+05:30');
  });
});

describe('isoToIstInputs', () => {
  it('reads the IST date and time back from a UTC timestamp', () => {
    // 2026-12-01 03:30 UTC is 09:00 IST on the same day.
    expect(isoToIstInputs('2026-12-01T03:30:00Z')).toEqual({ date: '2026-12-01', time: '09:00' });
  });

  it('round-trips with istInputsToIso', () => {
    const iso = istInputsToIso('2026-12-15', '23:15');
    expect(isoToIstInputs(iso)).toEqual({ date: '2026-12-15', time: '23:15' });
  });
});
