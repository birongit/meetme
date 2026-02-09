import React from 'react';

const Header = () => {
  return (
    <header>
      <h1>Book a 60 min Meeting with Birgit</h1>
      <p className="meeting-description" style={{ maxWidth: '600px', margin: '0 auto 2rem auto', color: '#666', lineHeight: '1.5' }}>
        Let's discuss your project, ideas, or anything else you have in mind. 
        This is a casual chat to see how we can work together. Whether you're looking for technical advice, 
        a partnership, or just want to say hello, I'm happy to connect.
      </p>
    </header>
  );
};

export default Header;
