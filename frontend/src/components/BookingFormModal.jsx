import { useEffect, useState } from 'react';
import { bookingApi } from '../api/services.js';
import { errorMessage, formatTime, todayIst } from '../utils/format.js';
import { istInputsToIso, isoToIstInputs } from '../utils/istTime.js';

const DURATION_OPTIONS = [0.5, 1, 1.5, 2, 3, 4, 6, 8, 10, 12];
const MAX_ADVANCE_DAYS = 14;
const DEBOUNCE_MS = 300;

function maxDateIst() {
  const [year, month, day] = todayIst().split('-').map(Number);
  return new Date(Date.UTC(year, month - 1, day + MAX_ADVANCE_DAYS)).toISOString().slice(0, 10);
}

function initialState(booking) {
  if (!booking) {
    return { date: todayIst(), time: '09:00', duration: 1, slotId: '' };
  }
  const { date, time } = isoToIstInputs(booking.start_time);
  return { date, time, duration: booking.duration_minutes / 60, slotId: booking.slot_id };
}

function durationLabel(hours) {
  return hours < 1 ? '30 min' : `${hours} h`;
}

export default function BookingFormModal({ booking, vehicleType, onClose, onSaved }) {
  const isEdit = Boolean(booking);
  const [form, setForm] = useState(() => initialState(booking));
  const [slots, setSlots] = useState([]);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState(null);
  const [saving, setSaving] = useState(false);

  const startIso = form.date && form.time ? istInputsToIso(form.date, form.time) : null;
  const endIso = startIso
    ? new Date(new Date(startIso).getTime() + form.duration * 60 * 60 * 1000).toISOString()
    : null;

  // Load the slots free for the chosen window. Debounced so typing does not send a request per keystroke.
  useEffect(() => {
    if (!startIso || !endIso || new Date(startIso) <= new Date()) {
      setSlots([]);
      return undefined;
    }
    setLoadingSlots(true);
    const timer = window.setTimeout(async () => {
      try {
        const response = await bookingApi.availableSlots(startIso, endIso, booking?.vehicle_type || vehicleType);
        let options = response.data.slots;
        // While editing, the booking's own slot looks busy for its own window, so keep it as an option.
        if (isEdit && !options.some((slot) => slot.slot_id === booking.slot_id)) {
          options = [{ slot_id: booking.slot_id, floor: booking.slot_id.split('-')[0], location: 'Current slot' }, ...options];
        }
        setSlots(options);
        setForm((current) => (options.some((slot) => slot.slot_id === current.slotId) ? current : { ...current, slotId: '' }));
      } catch (error) {
        setSlots([]);
        setServerError(errorMessage(error));
      } finally {
        setLoadingSlots(false);
      }
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startIso, endIso]);

  function setField(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  function validate() {
    const next = {};
    if (!form.date) next.date = 'Choose a date.';
    if (!form.time) next.time = 'Choose a start time.';
    if (startIso && new Date(startIso) <= new Date()) next.time = 'Choose a start time in the future.';
    if (!form.slotId) next.slotId = 'Choose a slot that is free for this time.';
    return next;
  }

  async function handleSave(event) {
    event.preventDefault();
    setServerError(null);
    const next = validate();
    setErrors(next);
    if (Object.keys(next).length) return;

    setSaving(true);
    const payload = { slot_id: form.slotId, start_time: startIso, end_time: endIso };
    try {
      const response = isEdit ? await bookingApi.update(booking.id, payload) : await bookingApi.create(payload);
      onSaved(response.message);
    } catch (error) {
      setServerError(errorMessage(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="modal d-block" tabIndex="-1" role="dialog" aria-modal="true" aria-labelledby="booking-modal-title">
        <div className="modal-dialog modal-dialog-centered modal-dialog-scrollable">
          <div className="modal-content">
            <div className="modal-header">
              <h5 className="modal-title" id="booking-modal-title">{isEdit ? 'Edit booking' : 'New booking'}</h5>
              <button type="button" className="btn-close" aria-label="Close" onClick={onClose} />
            </div>
            <div className="modal-body">
              {serverError && <div className="alert alert-danger py-2 small">{serverError}</div>}
              <form id="booking-form" onSubmit={handleSave} noValidate className="row g-3">
                <div className="col-md-6">
                  <label className="form-label small fw-semibold" htmlFor="booking-date">Date</label>
                  <input id="booking-date" type="date" className={`form-control ${errors.date ? 'is-invalid' : ''}`} min={todayIst()} max={maxDateIst()} value={form.date} onChange={(e) => setField('date', e.target.value)} />
                  {errors.date && <div className="invalid-feedback">{errors.date}</div>}
                </div>
                <div className="col-md-3">
                  <label className="form-label small fw-semibold" htmlFor="booking-start">Start (IST)</label>
                  <input id="booking-start" type="time" className={`form-control ${errors.time ? 'is-invalid' : ''}`} value={form.time} onChange={(e) => setField('time', e.target.value)} />
                  {errors.time && <div className="invalid-feedback">{errors.time}</div>}
                </div>
                <div className="col-md-3">
                  <label className="form-label small fw-semibold" htmlFor="booking-duration">Duration</label>
                  <select id="booking-duration" className="form-select" value={form.duration} onChange={(e) => setField('duration', Number(e.target.value))}>
                    {DURATION_OPTIONS.map((hours) => (
                      <option key={hours} value={hours}>{durationLabel(hours)}</option>
                    ))}
                  </select>
                </div>
                <div className="col-12">
                  <label className="form-label small fw-semibold" htmlFor="booking-slot">
                    Slot for {booking?.vehicle_type || vehicleType || 'vehicle'}s {loadingSlots && <span className="spinner-border spinner-border-sm ms-1" />}
                  </label>
                  <select id="booking-slot" className={`form-select ${errors.slotId ? 'is-invalid' : ''}`} value={form.slotId} onChange={(e) => setField('slotId', e.target.value)} disabled={!startIso || loadingSlots}>
                    <option value="">{slots.length ? 'Choose a free slot' : 'No free slots for this time'}</option>
                    {slots.map((slot) => (
                      <option key={slot.slot_id} value={slot.slot_id}>{slot.slot_id} · Floor {slot.floor} · {slot.location}</option>
                    ))}
                  </select>
                  {errors.slotId && <div className="invalid-feedback">{errors.slotId}</div>}
                  <div className="form-text">
                    {startIso ? `Window: ${form.date} ${formatTime(startIso)} to ${formatTime(endIso)} IST.` : 'Choose a date and time to see free slots.'}
                    {' '}Bookings can start up to {MAX_ADVANCE_DAYS} days ahead.
                  </div>
                </div>
              </form>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-outline-secondary" onClick={onClose} disabled={saving}>Cancel</button>
              <button type="submit" form="booking-form" className="btn btn-primary" disabled={saving}>
                {saving && <span className="spinner-border spinner-border-sm me-2" />}
                {isEdit ? 'Save changes' : 'Book slot'}
              </button>
            </div>
          </div>
        </div>
      </div>
      <div className="modal-backdrop show" />
    </>
  );
}
