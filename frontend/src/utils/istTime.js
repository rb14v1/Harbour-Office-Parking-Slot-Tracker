export const IST_OFFSET = '+05:30';
const IST_ZONE = 'Asia/Kolkata';

/** Builds an ISO timestamp with the IST offset from a YYYY-MM-DD date and HH:MM time. */
export function istInputsToIso(dateString, timeString) {
  return `${dateString}T${timeString}:00${IST_OFFSET}`;
}

/** Splits an ISO timestamp into the IST date and time that form inputs use. */
export function isoToIstInputs(isoString) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: IST_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date(isoString));
  const value = (type) => parts.find((part) => part.type === type).value;
  return {
    date: `${value('year')}-${value('month')}-${value('day')}`,
    time: `${value('hour')}:${value('minute')}`,
  };
}

/** Milliseconds from now until the given IST date and time. */
export function msUntilIst(dateString, timeString) {
  return new Date(istInputsToIso(dateString, timeString)).getTime() - Date.now();
}
