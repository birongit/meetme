import React, { useState } from 'react';
import './App.css';

// Components
import Header from './components/Header';
import UserForm from './components/UserForm';
import SlotList from './components/SlotList';
import FeedbackForm from './components/FeedbackForm';
import DebugPanel from './components/DebugPanel';

// Hooks & Utils
import { useBooking } from './hooks/useBooking';
import { validateEmail } from './utils/validation';

function App() {
  const isDev = process.env.NODE_ENV === 'development';

  // UI State
  const [showDebug, setShowDebug] = useState(false);
  const [testMode, setTestMode] = useState(false);
  const [feedback, setFeedback] = useState("");
  
  // User Form State
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [emailError, setEmailError] = useState("");
  const [nameError, setNameError] = useState("");

  // Logic Hook
  const { 
    slots,
    loading,
    message,
    llmInput,
    llmOutput,
    bookingStatus,
    timezone,
    fetchSlots,
    bookSlot
  } = useBooking();

  const handleFetch = () => {
    fetchSlots(feedback, isDev && testMode);
  };

  const handleBook = async (slot) => {
    let hasError = false;
    if (!firstName.trim() || !lastName.trim()) {
      setNameError("Please enter your first and last name.");
      hasError = true;
    } else {
      setNameError("");
    }

    if (email && !validateEmail(email)) {
      setEmailError("Please enter a valid email address.");
      hasError = true;
    } else {
      setEmailError("");
    }

    if (hasError) return;

    await bookSlot(slot, { email, firstName, lastName });
  };

  const hasSuccessfulBooking = Object.values(bookingStatus).some(s => s.status === 'success');

  return (
    <div className="App">
      <Header />
      
      <button onClick={handleFetch} disabled={loading} className="fetch-button">
        {loading ? 'Thinking...' : 'Find Available Slots'}
      </button>

      {slots.length > 0 && (
        <div className="booking-section">
          <UserForm 
            firstName={firstName} setFirstName={setFirstName}
            lastName={lastName} setLastName={setLastName}
            email={email} setEmail={setEmail}
            nameError={nameError} setNameError={setNameError}
            emailError={emailError} setEmailError={setEmailError}
          />

          <SlotList
            slots={slots}
            bookingStatus={bookingStatus}
            onBook={handleBook}
            hasSuccessfulBooking={hasSuccessfulBooking}
            timezone={timezone}
          />

          <FeedbackForm 
            feedback={feedback}
            setFeedback={setFeedback}
            onFetch={handleFetch}
            loading={loading}
          />
        </div>
      )}
      
      {message && <div className="message">{message}</div>}

      {isDev && (
        <DebugPanel
          showDebug={showDebug} setShowDebug={setShowDebug}
          testMode={testMode} setTestMode={setTestMode}
          llmInput={llmInput} llmOutput={llmOutput}
        />
      )}
    </div>
  );
}

export default App;
