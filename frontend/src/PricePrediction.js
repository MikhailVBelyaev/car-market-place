import React, { useState, useEffect } from 'react';
import axios from 'axios';

const PricePrediction = () => {
  const [formData, setFormData] = useState({ year: '', mileage: '', brand: '', model: '', color: '', gear_type: '', fuel_type: '', body_type: '' });
  const [prediction, setPrediction] = useState(null);
  const [error, setError] = useState(null);

  const [dropdownOptions, setDropdownOptions] = useState({
    brand: [],
    model: [],
    color: [],
    gear_type: [],
    fuel_type: [],
    body_type: [],
  });

  useEffect(() => {
    axios.get('/api/cars/dropdown-options/')
      .then((response) => {
        setDropdownOptions(response.data);
      })
      .catch((error) => {
        console.error('Error fetching dropdown options:', error);
      });
  }, []);

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
    fetch('/predict2', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        year: parseInt(formData.year),
        mileage: parseInt(formData.mileage),
        brand: formData.brand,
        model: formData.model,
        color: formData.color,
        gear_type: formData.gear_type,
        fuel_type: formData.fuel_type,
        body_type: formData.body_type,
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
          Brand:
        </label>
        <select
          name="brand"
          value={formData.brand}
          onChange={handleInputChange}
          style={inputStyle}
        >
          <option value="">Select Brand</option>
          {dropdownOptions.brand.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
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
          Model:
        </label>
        <select
          name="model"
          value={formData.model}
          onChange={handleInputChange}
          style={inputStyle}
        >
          <option value="">Select Model</option>
          {dropdownOptions.model.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
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
          Color:
        </label>
        <select
          name="color"
          value={formData.color}
          onChange={handleInputChange}
          style={inputStyle}
        >
          <option value="">Select Color</option>
          {dropdownOptions.color.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
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
          Gear Type:
        </label>
        <select
          name="gear_type"
          value={formData.gear_type}
          onChange={handleInputChange}
          style={inputStyle}
        >
          <option value="">Select Gear Type</option>
          {dropdownOptions.gear_type.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
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
          Fuel Type:
        </label>
        <select
          name="fuel_type"
          value={formData.fuel_type}
          onChange={handleInputChange}
          style={inputStyle}
        >
          <option value="">Select Fuel Type</option>
          {dropdownOptions.fuel_type.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
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
          Body Type:
        </label>
        <select
          name="body_type"
          value={formData.body_type}
          onChange={handleInputChange}
          style={inputStyle}
        >
          <option value="">Select Body Type</option>
          {dropdownOptions.body_type.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
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