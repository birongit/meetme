import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const api = {
  suggestSlots: async (timezone, feedback, testMode) => {
    const response = await axios.post(`${API_URL}/booking/suggest-ai`, {
      timezone,
      user_feedback: feedback,
      test_mode: testMode
    });
    return response.data;
  },

  bookSlot: async (slot, userDetails) => {
    const response = await axios.post(`${API_URL}/booking/book`, {
      start: slot.raw.start,
      end: slot.raw.end,
      email: userDetails.email,
      first_name: userDetails.firstName,
      last_name: userDetails.lastName
    });
    return response.data;
  }
};
