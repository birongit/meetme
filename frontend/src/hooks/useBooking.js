import { useState } from 'react';
import { api } from '../services/api';

export const useBooking = () => {
  const [slots, setSlots] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [hasFeedback, setHasFeedback] = useState(false);
  const [llmInput, setLlmInput] = useState(null);
  const [llmOutput, setLlmOutput] = useState(null);
  const [agentSteps, setAgentSteps] = useState([]);
  const [bookingStatus, setBookingStatus] = useState({});
  const [timezone] = useState(() => Intl.DateTimeFormat().resolvedOptions().timeZone);
  // Groups all suggest requests from this visit into one Langfuse session
  const [sessionId] = useState(() =>
    (window.crypto && window.crypto.randomUUID) ? window.crypto.randomUUID() : `s-${Date.now()}-${Math.random().toString(36).slice(2)}`
  );

  const fetchSlots = async (feedback, testMode) => {
    setLoading(true);
    setMessage("");
    setHasFeedback(!!feedback);
    setLlmInput(null);
    setLlmOutput(null);
    setAgentSteps([]);
    
    try {
      const data = await api.suggestSlots(timezone, feedback, testMode, sessionId);
      
      if (data.llm_input) setLlmInput(data.llm_input);
      if (data.llm_output) setLlmOutput(data.llm_output);
      if (data.agent_steps) setAgentSteps(data.agent_steps);
      if (data.ai_message) setMessage(data.ai_message);

      const parsedSlots = data.suggested_slots.map(slot => ({
        start: new Date(slot.start),
        end: new Date(slot.end),
        raw: slot
      }));
      
      parsedSlots.sort((a, b) => a.start - b.start);
      setSlots(parsedSlots);
    } catch (err) {
      setMessage(
        err.response && err.response.data && err.response.data.error
          ? `Error fetching slots: ${err.response.data.error}`
          : "Error fetching slots"
      );
    }
    setLoading(false);
  };

  const bookSlot = async (slot, userDetails) => {
    const slotKey = slot.raw.start;
    setBookingStatus(prev => ({ ...prev, [slotKey]: { status: 'loading' } }));

    try {
      const data = await api.bookSlot(slot, userDetails);
      setBookingStatus(prev => ({ 
        ...prev, 
        [slotKey]: { status: 'success', message: data.message || 'Booking successful!' } 
      }));
      return true;
    } catch (err) {
      const errorMsg = err.response && err.response.data && err.response.data.error
          ? err.response.data.error
          : 'Error booking slot';
      setBookingStatus(prev => ({ 
        ...prev, 
        [slotKey]: { status: 'error', message: errorMsg } 
      }));
      return false;
    }
  };

  return {
    slots,
    loading,
    message,
    hasFeedback,
    llmInput,
    llmOutput,
    agentSteps,
    bookingStatus,
    timezone,
    fetchSlots,
    bookSlot
  };
};
