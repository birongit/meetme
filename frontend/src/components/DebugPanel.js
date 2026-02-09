import React from 'react';

const DebugPanel = ({ showDebug, setShowDebug, testMode, setTestMode, llmInput, llmOutput }) => {
  return (
    <div className="debug-section" style={{ marginTop: '3rem', borderTop: '1px solid #eee', paddingTop: '1rem' }}>
      <div style={{ marginBottom: '1rem', display: 'flex', gap: '1rem', justifyContent: 'center' }}>
        <label style={{ cursor: 'pointer', color: '#999', fontSize: '0.8rem' }}>
          <input 
            type="checkbox" 
            checked={showDebug} 
            onChange={e => setShowDebug(e.target.checked)}
            style={{ marginRight: '0.5rem' }}
          />
          Show Debug Info
        </label>
        <label style={{ cursor: 'pointer', color: '#999', fontSize: '0.8rem' }}>
          <input 
            type="checkbox" 
            checked={testMode} 
            onChange={e => setTestMode(e.target.checked)}
            style={{ marginRight: '0.5rem' }}
          />
          Test Mode (Mock Data)
        </label>
      </div>

      {showDebug && (
        <div style={{ textAlign: 'left', background: '#f5f5f5', padding: '1rem', borderRadius: '4px', fontSize: '0.8rem', overflowX: 'auto' }}>
          <h4>Debug Info</h4>
          {llmInput && (
            <div style={{ marginBottom: '1rem' }}>
              <strong>LLM Input:</strong>
              <pre>{llmInput}</pre>
            </div>
          )}
          {llmOutput && (
            <div>
              <strong>LLM Output:</strong>
              <pre>{JSON.stringify(JSON.parse(llmOutput), null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DebugPanel;
