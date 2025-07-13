import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import CarList from './CarList';
import PricePrediction from './PricePrediction';

const menuItems = [
  { label: 'List Cars', path: '/cars', icon: 'M11.62 17.08c-.13.05-.23.12-.33.21...', category: 'cars' },
  { label: 'Predict Price', path: '/predict', icon: 'M8.199 14.667a1 1 0 1 0-1.886...', category: 'predict' },
];

const MainSite = () => {
  const menuStyle = {
    display: 'flex',
    justifyContent: 'center',
    background: '#fff',
    padding: '10px 0',
    borderBottom: '1px solid #eee',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    position: 'sticky',
    top: '68px',
    zIndex: 150,
  };

  const menuItemStyle = {
    margin: '0 15px',
    listStyle: 'none',
  };

  const linkStyle = {
    display: 'flex',
    alignItems: 'center',
    textDecoration: 'none',
    color: 'rgba(7, 7, 7, 1)',
    fontFamily: 'Amazon Ember, Arial, sans-serif',
    fontSize: '16px',
    fontWeight: 500,
    padding: '8px 12px',
    borderRadius: '4px',
    transition: 'background 0.2s',
  };

  const linkHoverStyle = {
    background: '#f5f5f5',
  };

  return (
    <Router>
      <header
        style={{
          width: '100%',
          position: 'fixed',
          left: 0,
          top: 0,
          zIndex: 200,
          background: 'linear-gradient(90deg, #2874f0 0%, #0057b8 100%)',
          color: '#fff',
          minHeight: '68px',
          display: 'flex',
          alignItems: 'center',
          boxShadow: '0 2px 10px 0 rgba(40,116,240,0.10)',
          padding: '0 20px',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            width: '100%',
            maxWidth: '1200px',
            margin: '0 auto',
            justifyContent: 'space-between',
            padding: '0 10px',
          }}
        >
          <h1
            style={{
              fontFamily: 'Amazon Ember, Arial, sans-serif',
              fontWeight: 900,
              fontSize: '2.2rem',
              letterSpacing: '2px',
              margin: '0 20px 0 0',
              color: '#fff',
              textShadow: '0 2px 8px #0057b899',
            }}
          >
            Mooods
          </h1>
        </div>
      </header>
      <div data-widget="horizontalMenu" style={menuStyle}>
        <ul style={{ display: 'flex', listStyle: 'none', margin: 0, padding: 0 }}>
          {menuItems.map((item) => (
            <li key={item.category} style={menuItemStyle}>
              <Link
                to={item.path}
                style={linkStyle}
                onMouseOver={(e) => Object.assign(e.currentTarget.style, linkHoverStyle)}
                onMouseOut={(e) => Object.assign(e.currentTarget.style, linkStyle)}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  style={{ marginRight: '8px' }}
                >
                  <path fill="currentColor" d={item.icon} />
                </svg>
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      </div>
      <main style={{ paddingTop: '120px', maxWidth: '1200px', margin: '0 auto' }}>
        <Routes>
          <Route path="/cars" element={<CarList />} />
          <Route path="/predict" element={<PricePrediction />} />
          <Route path="/" element={<CarList />} />
        </Routes>
      </main>
    </Router>
  );
};

export default MainSite;