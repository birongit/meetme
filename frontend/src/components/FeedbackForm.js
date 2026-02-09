import React from 'react';

const FeedbackForm = ({ feedback, setFeedback, onFetch, loading }) => {
  return (
    <div className="feedback-section" style={{ marginTop: '3rem', padding: '1.5rem', background: '#fff3cd', borderRadius: '8px', border: '1px solid #ffeeba' }}>
      <h4 style={{ marginTop: 0, color: '#856404' }}>None of these work?</h4>
      <p style={{ fontSize: '0.9rem', color: '#856404' }}>Tell us what you're looking for, and we'll find better options.</p>
      <div style={{ display: 'flex', gap: '10px' }}>
        <input 
          type="text" 
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !loading && feedback.trim()) {
              onFetch();
            }
          }}
          placeholder="e.g. 'I need a weekend slot' or 'Any early mornings?'"
          style={{ flex: 1, padding: '10px', borderRadius: '4px', border: '1px solid #ccc' }}
        />
        <button 
          onClick={onFetch} 
          disabled={loading || !feedback.trim()}
          style={{ 
            padding: '10px 20px', 
            background: '#856404', 
            color: 'white', 
            border: 'none', 
            borderRadius: '4px', 
            cursor: 'pointer',
            opacity: (loading || !feedback.trim()) ? 0.7 : 1
          }}
        >
          {loading ? 'Thinking...' : 'Find Alternatives'}
        </button>
      </div>
    </div>
  );
};

export default FeedbackForm;
