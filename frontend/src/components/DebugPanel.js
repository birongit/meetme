import React from 'react';

const DebugPanel = ({ showDebug, setShowDebug, testMode, setTestMode, llmInput, llmOutput, agentSteps }) => {
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
          {agentSteps && agentSteps.length > 0 && (
            <div style={{ marginBottom: '1rem' }}>
              <strong>Agent Tool Calls ({agentSteps.length}):</strong>
              {agentSteps.map((step, i) => (
                <div key={i} style={{ background: '#e8f4e8', padding: '0.5rem', margin: '0.5rem 0', borderRadius: '4px', borderLeft: '3px solid #4caf50' }}>
                  <div><strong>{step.tool}</strong>({JSON.stringify(step.input)})</div>
                  <pre style={{ margin: '0.25rem 0 0', whiteSpace: 'pre-wrap' }}>{step.output}</pre>
                </div>
              ))}
            </div>
          )}
          {agentSteps && agentSteps.length === 0 && llmOutput && (
            <div style={{ marginBottom: '1rem', color: '#999', fontStyle: 'italic' }}>
              No tool calls made by agent.
            </div>
          )}
          {llmOutput && (
            <div>
              <strong>LLM Output:</strong>
              <pre>{llmOutput}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default DebugPanel;
