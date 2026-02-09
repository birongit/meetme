import { render, screen } from '@testing-library/react';
import App from '../App';

test('renders booking page heading', () => {
  render(<App />);
  const heading = screen.getByText(/Book a 60 min Meeting with Birgit/i);
  expect(heading).toBeInTheDocument();
});
