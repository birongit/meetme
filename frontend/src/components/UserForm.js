import React from 'react';

const UserForm = ({ 
  firstName, setFirstName, 
  lastName, setLastName, 
  email, setEmail, 
  nameError, setNameError, 
  emailError, setEmailError 
}) => {
  return (
    <div className="input-container" style={{ marginBottom: '2rem', padding: '1rem', background: '#f0f8ff', borderRadius: '8px' }}>
      <div style={{ marginBottom: '1rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold', color: '#333' }}>
          What is your name?
        </label>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="First Name"
            value={firstName}
            onChange={(e) => {
              setFirstName(e.target.value);
              if (nameError) setNameError("");
            }}
            style={{
              flex: '1 1 140px',
              padding: '10px',
              border: nameError ? '1px solid red' : '1px solid #ccc',
              borderRadius: '4px',
              fontSize: '1rem',
              boxSizing: 'border-box'
            }}
          />
          <input
            type="text"
            placeholder="Last Name"
            value={lastName}
            onChange={(e) => {
              setLastName(e.target.value);
              if (nameError) setNameError("");
            }}
            style={{
              flex: '1 1 140px',
              padding: '10px',
              border: nameError ? '1px solid red' : '1px solid #ccc',
              borderRadius: '4px',
              fontSize: '1rem',
              boxSizing: 'border-box'
            }}
          />
        </div>
        {nameError && <div style={{ color: 'red', fontSize: '0.8rem', marginTop: '0.5rem' }}>{nameError}</div>}
      </div>

      <div>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold', color: '#333' }}>
          Where should we send the invite?
        </label>
        <div>
          <input
            type="email"
            placeholder="Enter your email address"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (emailError) setEmailError("");
            }}
            style={{ 
              padding: '10px', 
              width: '100%', 
              border: emailError ? '1px solid red' : '1px solid #ccc',
              borderRadius: '4px',
              fontSize: '1rem',
              boxSizing: 'border-box'
            }}
          />
        </div>
        {emailError && <div style={{ color: 'red', fontSize: '0.8rem', marginTop: '0.5rem' }}>{emailError}</div>}
      </div>
    </div>
  );
};

export default UserForm;
