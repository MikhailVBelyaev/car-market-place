import React, { useState } from 'react';

const PricePrediction = () => {
  const [formData, setFormData] = useState({ year: '', mileage: '' });
  const [prediction, setPrediction] = useState(null);
  const [error, setError] = useState(null);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handlePredict = () => {
    if (!formData.year || !formData.mileage) {
      setError('Please enter both year and mileage.');
      return;
    }
    setError(null);
    fetch('/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        year: parseInt(formData.year),
        mileage: parseInt(formData.mileage),
      }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setPrediction(data.predicted_price);
      })
      .catch((err) => {
        console.error('Error fetching prediction:', err);
        setError('Failed to fetch prediction. Please try again.');
      });
  };

  const inputStyle = {
    width: '100%',
    padding: '10px',
    marginBottom: '15px',
    borderRadius: '4px',
    border: '1px solid #ccc',
    fontFamily: 'Amazon Ember, Arial, sans-serif',
    fontSize: '15px',
  };

  const buttonStyle = {
    padding: '10px 20px',
    cursor: 'pointer',
    background: 'linear-gradient(90deg, #2874f0 0%, #0057b8 100%)',
    color: '#fff',
    border: 'none',
    borderRadius: '20px',
    fontWeight: 600,
    fontSize: '15px',
    boxShadow: '0 2px 6px 0 rgba(40,116,240,0.15)',
    transition: 'background 0.2s, box-shadow 0.2s, transform 0.1s',
  };

  const buttonHoverStyle = {
    background: 'linear-gradient(90deg, #0057b8 0%, #2874f0 100%)',
    boxShadow: '0 4px 16px 0 rgba(40,116,240,0.25)',
    transform: 'translateY(-2px) scale(1.03)',
  };

  return (
    <div style={{ padding: '20px', maxWidth: '600px', margin: '0 auto' }}>
      <h2
        style={{
          fontFamily: 'Amazon Ember, Arial, sans-serif',
          fontWeight: 700,
          fontSize: '1.5rem',
          marginBottom: '20px',
          color: '#222',
        }}
      >
        Predict Car Price
      </h2>
      <div>
        <label
          style={{
            display: 'block',
            marginBottom: '5px',
            fontFamily: 'Amazon Ember, Arial, sans-serif',
            fontSize: '15px',
            fontWeight: 500,
          }}
        >
          Year:
        </label>
        <input
          type="number"
          name="year"
          value={formData.year}
          onChange={handleInputChange}
          style={inputStyle}
          placeholder="e.g., 2020"
        />
      </div>
      <div>
        <label
          style={{
            display: 'block',
            marginBottom: '5px',
            fontFamily: 'Amazon Ember, Arial, sans-serif',
            fontSize: '15px',
            fontWeight: 500,
          }}
        >
          Mileage (km):
        </label>
        <input
          type="number"
          name="mileage"
          value={formData.mileage}
          onChange={handleInputChange}
          style={inputStyle}
          placeholder="e.g., 50000"
        />
      </div>
      <button
        onClick={handlePredict}
        style={buttonStyle}
        onMouseOver={(e) => Object.assign(e.currentTarget.style, buttonHoverStyle)}
        onMouseOut={(e) => Object.assign(e.currentTarget.style, buttonStyle)}
      >
        Predict Price
      </button>
      {prediction && (
        <p
          style={{
            marginTop: '20px',
            fontFamily: 'Amazon Ember, Arial, sans-serif',
            fontSize: '16px',
            color: '#222',
          }}
        >
          Predicted Price: ${prediction.toFixed(2)} USD
        </p>
      )}
      {error && (
        <p
          style={{
            marginTop: '20px',
            fontFamily: 'Amazon Ember, Arial, sans-serif',
            fontSize: '16px',
            color: 'red',
          }}
        >
          {error}
        </p>
      )}
    </div>
  );
};

export default PricePrediction;