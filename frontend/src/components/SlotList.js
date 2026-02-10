import React from 'react';

const SlotList = ({ slots, bookingStatus, onBook, hasSuccessfulBooking, timezone }) => {
  // Group slots by date
  const groupedSlots = slots.reduce((acc, slot) => {
    const dateStr = slot.start.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    if (!acc[dateStr]) {
      acc[dateStr] = [];
    }
    acc[dateStr].push(slot);
    return acc;
  }, {});

  return (
    <div className="slots-container">
      {timezone && (
        <div style={{ textAlign: 'right', fontSize: '0.85rem', color: '#6c757d', marginBottom: '-1rem' }}>
          Times shown in {timezone.replace(/_/g, ' ')}
        </div>
      )}
      {Object.keys(groupedSlots).map(date => (
        <div key={date} className="day-group">
          <h3 className="day-header">{date}</h3>
          <div className="slots-grid">
            {groupedSlots[date].map((slot, idx) => {
              const slotKey = slot.raw.start;
              const status = bookingStatus[slotKey] || { status: 'idle' };
              const isBooked = status.status === 'success';
              const isOtherSlotDisabled = hasSuccessfulBooking && !isBooked;

              return (
                <div key={idx} className={`slot-card ${isOtherSlotDisabled ? 'disabled-slot' : ''}`}>
                  <div className="slot-time">
                    {slot.start.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})} – {slot.end.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                  </div>
                  
                  {isBooked ? (
                    <div style={{color: 'green', marginTop: '0.5rem', fontWeight: 'bold'}}>
                      ✓ {status.message}
                    </div>
                  ) : (
                    <>
                      <button 
                        className="book-button" 
                        onClick={() => onBook(slot)}
                        disabled={status.status === 'loading' || isOtherSlotDisabled}
                      >
                        {status.status === 'loading' ? 'Booking...' : 'Book'}
                      </button>
                      {status.status === 'error' && (
                        <div style={{color: 'red', fontSize: '0.8rem', marginTop: '0.5rem'}}>
                          {status.message}
                        </div>
                      )}
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};

export default SlotList;
