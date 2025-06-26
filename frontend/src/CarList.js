import React, { useState, useEffect } from 'react';

const API_URL = "/api/cars/filtered-list/";

function CarList() {
  const [cars, setCars] = useState([]);
  const [filters, setFilters] = useState({
    fuel_type: '',
    gear_type: '',
    color: '',
    vehicle_type: '',
    condition: '',
    brand: '',
    model: '',
    year: '',
    price: '',
    mileage: ''
  });
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 10;

  const fetchCars = () => {
    const query = new URLSearchParams();
    for (const key in filters) {
      if (filters[key]) {
        query.append(key, filters[key]);
      }
    }

    fetch(`${API_URL}?${query.toString()}`)
      .then(res => res.json())
      .then(data => {
        setCars(data);
        setCurrentPage(1);
      })
      .catch(err => console.error(err));
  };

  useEffect(() => {
    fetchCars(); // initial load
  }, []);

  const handleChange = (e) => {
    setFilters({ ...filters, [e.target.name]: e.target.value });
  };

  // For mileage range checkboxes
  const handleMileageRangeClick = (range) => {
    setFilters(prevFilters => ({ ...prevFilters, mileage: range }));
    setCurrentPage(1);
    // Fetch cars after updating filters
    const updatedFilters = { ...filters, mileage: range };
    const query = new URLSearchParams();
    for (const key in updatedFilters) {
      if (updatedFilters[key]) {
        query.append(key, updatedFilters[key]);
      }
    }
    fetch(`${API_URL}?${query.toString()}`)
      .then(res => res.json())
      .then(data => {
        setCars(data);
      })
      .catch(err => console.error(err));
  };
  const mileageRanges = [
    { label: 'Under 50,000 km', value: '0-50000' },
    { label: '50,000 - 100,000 km', value: '50000-100000' },
    { label: '100,000 - 150,000 km', value: '100000-150000' },
    { label: '150,000 - 200,000 km', value: '150000-200000' },
    { label: 'Over 200,000 km', value: '200000-' }
  ];

  const handlePriceRangeClick = (range) => {
    setFilters(prevFilters => ({ ...prevFilters, price: range }));
    setCurrentPage(1);
    // Fetch cars after updating filters
    const updatedFilters = { ...filters, price: range };
    const query = new URLSearchParams();
    for (const key in updatedFilters) {
      if (updatedFilters[key]) {
        query.append(key, updatedFilters[key]);
      }
    }
    fetch(`${API_URL}?${query.toString()}`)
      .then(res => res.json())
      .then(data => {
        setCars(data);
      })
      .catch(err => console.error(err));
  };

  const handleFuelTypeClick = (type) => {
    const newFuelType = filters.fuel_type === type ? '' : type;
    setFilters(prevFilters => ({ ...prevFilters, fuel_type: newFuelType }));
    setCurrentPage(1);
    const updatedFilters = { ...filters, fuel_type: newFuelType };
    const query = new URLSearchParams();
    for (const key in updatedFilters) {
      if (updatedFilters[key]) {
        query.append(key, updatedFilters[key]);
      }
    }
    fetch(`${API_URL}?${query.toString()}`)
      .then(res => res.json())
      .then(data => {
        setCars(data);
      })
      .catch(err => console.error(err));
  };

  const totalPages = Math.ceil(cars.length / rowsPerPage);
  const displayedCars = cars.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage);

  // Responsive sidebar and container style
  const sidebarStyle = {
    width: '250px',
    minWidth: '200px',
    padding: '20px',
    borderRight: '1px solid #ccc',
    height: '100vh',
    boxSizing: 'border-box',
    position: 'fixed',
    overflowY: 'auto',
    backgroundColor: '#f9f9f9',
    top: '0',
    left: '0',
    zIndex: 100,
  };

  const containerStyle = {
    marginLeft: '270px',
    padding: '20px',
    minHeight: '100vh',
    background: '#f5f7fa',
    boxSizing: 'border-box',
  };

  // Responsive table
  const tableStyle = {
    width: '100%',
    borderCollapse: 'separate',
    borderSpacing: '0',
    background: '#fff',
    borderRadius: '16px',
    overflow: 'hidden',
    boxShadow: '0 2px 16px 0 rgba(40,116,240,0.07)',
    margin: '0 0 20px 0'
  };

  const thTdStyle = {
    borderBottom: '1px solid #eee',
    padding: '14px 12px',
    textAlign: 'left',
    fontSize: '16px',
    fontFamily: 'Amazon Ember, Arial, sans-serif'
  };

  const paginationStyle = {
    marginTop: '15px',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '12px',
    fontFamily: 'Amazon Ember, Arial, sans-serif'
  };

  const priceRanges = [
    { label: 'Under $5,000', value: '0-5000' },
    { label: '$5,000 - $10,000', value: '5000-10000' },
    { label: '$10,000 - $20,000', value: '10000-20000' },
    { label: '$20,000 - $50,000', value: '20000-50000' },
    { label: 'Over $50,000', value: '50000-' }
  ];

  const fuelTypes = [
    { label: 'Petrol', value: 'Petrol' },
    { label: 'Diesel', value: 'Diesel' },
    { label: 'Electric', value: 'Electric' }
  ];

  // Predefined options for gear_type, brand, and year
  const gearTypes = [
    { label: 'Automatic', value: 'Automatic' },
    { label: 'Manual', value: 'Manual' },
    { label: 'CVT', value: 'CVT' }
  ];

  const brands = [
    { label: 'Toyota', value: 'Toyota' },
    { label: 'Honda', value: 'Honda' },
    { label: 'BMW', value: 'BMW' },
    { label: 'Ford', value: 'Ford' },
    { label: 'Chevrolet', value: 'Chevrolet' }
  ];

  const years = [
    { label: '2024', value: '2024' },
    { label: '2023', value: '2023' },
    { label: '2022', value: '2022' },
    { label: '2021', value: '2021' },
    { label: '2020', value: '2020' },
    { label: '2019', value: '2019' },
    { label: '2018', value: '2018' }
  ];

  // Generic handler for filters with checkbox style (single select)
  const handleCheckboxFilterClick = (filterKey, value) => {
    const newValue = filters[filterKey] === value ? '' : value;
    setFilters(prevFilters => ({ ...prevFilters, [filterKey]: newValue }));
    setCurrentPage(1);
    const updatedFilters = { ...filters, [filterKey]: newValue };
    const query = new URLSearchParams();
    for (const key in updatedFilters) {
      if (updatedFilters[key]) {
        query.append(key, updatedFilters[key]);
      }
    }
    fetch(`${API_URL}?${query.toString()}`)
      .then(res => res.json())
      .then(data => {
        setCars(data);
      })
      .catch(err => console.error(err));
  };

  // Responsive header and search bar
  return (
    <>
      <header
        style={{
          width: '100%',
          position: 'fixed',
          left: 0,
          top: 0,
          zIndex: 200,
          background: 'linear-gradient(90deg, #2874f0 0%, #0057b8 100%)',
          color: '#fff',
          padding: '0 0 0 250px',
          minHeight: '68px',
          display: 'flex',
          alignItems: 'center',
          boxShadow: '0 2px 10px 0 rgba(40,116,240,0.10)',
        }}
      >
        <div style={{
          display: 'flex',
          alignItems: 'center',
          width: '100%',
          justifyContent: 'space-between',
          padding: '0 30px 0 0',
        }}>
          <h1 style={{
            fontFamily: 'Amazon Ember, Arial, sans-serif',
            fontWeight: 900,
            fontSize: '2.2rem',
            letterSpacing: '2px',
            margin: 0,
            color: '#fff',
            textShadow: '0 2px 8px #0057b899'
          }}>
            Mooods
          </h1>
          {/* Search Box */}
          <form
            onSubmit={e => {
              e.preventDefault();
              fetchCars();
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              background: '#fff',
              borderRadius: '30px',
              padding: '4px 10px',
              boxShadow: '0 2px 8px 0 rgba(0,0,0,0.05)'
            }}
          >
            <input
              type="text"
              placeholder="Search description, location, model..."
              value={filters.model}
              name="model"
              onChange={handleChange}
              style={{
                border: 'none',
                outline: 'none',
                padding: '7px 12px',
                borderRadius: '30px',
                fontSize: '15px',
                minWidth: '180px',
                background: 'transparent'
              }}
            />
            <button
              type="submit"
              style={{
                background: 'linear-gradient(90deg,#2874f0 0%,#0057b8 100%)',
                color: '#fff',
                border: 'none',
                borderRadius: '20px',
                fontWeight: 700,
                fontSize: '15px',
                padding: '7px 22px',
                marginLeft: '8px',
                cursor: 'pointer',
                boxShadow: '0 2px 6px 0 rgba(40,116,240,0.13)',
                transition: 'background 0.2s, box-shadow 0.2s'
              }}
            >
              Search
            </button>
          </form>
        </div>
      </header>
      <aside style={sidebarStyle}>
        <h2 style={{ fontFamily: 'Amazon Ember, Arial, sans-serif', fontWeight: 800, fontSize: '1.3rem', marginTop: '10px' }}>Filters</h2>
        <div style={{ display: 'flex', gap: '12px', marginBottom: '22px', alignItems: 'center' }}>
          <button
            onClick={fetchCars}
            style={{
              padding: '10px 20px',
              cursor: 'pointer',
              fontWeight: 600,
              background: 'linear-gradient(90deg, #2874f0 0%, #0057b8 100%)',
              color: '#fff',
              border: 'none',
              borderRadius: '20px',
              boxShadow: '0 2px 6px 0 rgba(40,116,240,0.15)',
              fontSize: '16px',
              letterSpacing: '0.5px',
              transition: 'background 0.2s, box-shadow 0.2s, transform 0.1s',
            }}
            onMouseOver={e => {
              e.currentTarget.style.background = 'linear-gradient(90deg, #0057b8 0%, #2874f0 100%)';
              e.currentTarget.style.boxShadow = '0 4px 16px 0 rgba(40,116,240,0.25)';
              e.currentTarget.style.transform = 'translateY(-2px) scale(1.03)';
            }}
            onMouseOut={e => {
              e.currentTarget.style.background = 'linear-gradient(90deg, #2874f0 0%, #0057b8 100%)';
              e.currentTarget.style.boxShadow = '0 2px 6px 0 rgba(40,116,240,0.15)';
              e.currentTarget.style.transform = '';
            }}
          >
            Show
          </button>
          <button
            onClick={() => {
              setFilters({
                fuel_type: '',
                gear_type: '',
                color: '',
                vehicle_type: '',
                condition: '',
                brand: '',
                model: '',
                year: '',
                price: '',
                mileage: ''
              });
              setCurrentPage(1);
              // Refetch with cleared filters
              setTimeout(fetchCars, 0);
            }}
            style={{
              padding: '10px 20px',
              cursor: 'pointer',
              background: 'linear-gradient(90deg, #ff5a36 0%, #c62828 100%)',
              color: '#fff',
              border: 'none',
              borderRadius: '20px',
              fontWeight: 600,
              fontSize: '16px',
              letterSpacing: '0.5px',
              boxShadow: '0 2px 6px 0 rgba(255,90,54,0.13)',
              transition: 'background 0.2s, box-shadow 0.2s, transform 0.1s',
            }}
            onMouseOver={e => {
              e.currentTarget.style.background = 'linear-gradient(90deg, #c62828 0%, #ff5a36 100%)';
              e.currentTarget.style.boxShadow = '0 4px 16px 0 rgba(255,90,54,0.22)';
              e.currentTarget.style.transform = 'translateY(-2px) scale(1.03)';
            }}
            onMouseOut={e => {
              e.currentTarget.style.background = 'linear-gradient(90deg, #ff5a36 0%, #c62828 100%)';
              e.currentTarget.style.boxShadow = '0 2px 6px 0 rgba(255,90,54,0.13)';
              e.currentTarget.style.transform = '';
            }}
          >
            Clear All Filters
          </button>
        </div>
        {/* All filter fields except price and model (model is search box) */}
        {Object.keys(filters).map((key) => {
          if (key === 'price' || key === 'model') return null;
          return (
            <div key={key} style={{ marginBottom: '12px' }}>
              <label htmlFor={key} style={{ textTransform: 'capitalize', display: 'block', marginBottom: '4px' }}>{key.replace('_', ' ')}:</label>
              <input
                type="text"
                id={key}
                name={key}
                value={filters[key]}
                onChange={handleChange}
                style={{ width: '100%', padding: '6px', boxSizing: 'border-box' }}
              />
            </div>
          )
        })}
        <div style={{ marginBottom: '24px' }}>
          <label style={{ textTransform: 'capitalize', display: 'block', marginBottom: '4px', fontWeight: 500, fontSize: '15px' }}>Mileage Range:</label>
          <div>
            {mileageRanges.map(range => (
              <label
                key={range.value}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  marginBottom: '6px',
                  cursor: 'pointer',
                  fontWeight: filters.mileage === range.value ? 600 : 400,
                  color: filters.mileage === range.value ? '#1a73e8' : '#000'
                }}
              >
                <input
                  type="checkbox"
                  checked={filters.mileage === range.value}
                  onChange={() => handleMileageRangeClick(filters.mileage === range.value ? '' : range.value)}
                  style={{ marginRight: '8px', accentColor: '#1a73e8' }}
                />
                {range.label}
              </label>
            ))}
            {filters.mileage && (
              <a
                href="#!"
                onClick={e => {
                  e.preventDefault();
                  handleMileageRangeClick('');
                }}
                style={{ display: 'block', marginTop: '8px', color: 'red', cursor: 'pointer', fontSize: '13px' }}
              >
                Clear mileage filter
              </a>
            )}
          </div>
        </div>
        <div style={{ marginBottom: '12px' }}>
          <label style={{ textTransform: 'capitalize', display: 'block', marginBottom: '4px' }}>Price:</label>
          <div>
            {priceRanges.map(range => (
              <a
                key={range.value}
                href="#!"
                onClick={(e) => {
                  e.preventDefault();
                  handlePriceRangeClick(range.value);
                }}
                style={{
                  display: 'block',
                  padding: '6px 0',
                  color: filters.price === range.value ? 'blue' : '#000',
                  cursor: 'pointer',
                  textDecoration: filters.price === range.value ? 'underline' : 'none'
                }}
              >
                {range.label}
              </a>
            ))}
            {filters.price && (
              <a
                href="#!"
                onClick={(e) => {
                  e.preventDefault();
                  handlePriceRangeClick('');
                }}
                style={{ display: 'block', marginTop: '8px', color: 'red', cursor: 'pointer' }}
              >
                Clear price filter
              </a>
            )}
          </div>
        </div>
        {/* Fuel Type Filter */}
        <div style={{ marginBottom: '24px' }}>
          <label style={{ textTransform: 'capitalize', display: 'block', marginBottom: '4px', fontWeight: 500, fontSize: '15px' }}>Fuel Type:</label>
          <div>
            {fuelTypes.map(type => (
              <label
                key={type.value}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  marginBottom: '6px',
                  cursor: 'pointer',
                  fontWeight: filters.fuel_type === type.value ? 600 : 400,
                  color: filters.fuel_type === type.value ? '#1a73e8' : '#000'
                }}
              >
                <input
                  type="checkbox"
                  checked={filters.fuel_type === type.value}
                  onChange={() => handleFuelTypeClick(type.value)}
                  style={{ marginRight: '8px', accentColor: '#1a73e8' }}
                />
                {type.label}
              </label>
            ))}
            {filters.fuel_type && (
              <a
                href="#!"
                onClick={e => {
                  e.preventDefault();
                  handleFuelTypeClick('');
                }}
                style={{ display: 'block', marginTop: '8px', color: 'red', cursor: 'pointer', fontSize: '13px' }}
              >
                Clear fuel type filter
              </a>
            )}
          </div>
        </div>
        {/* Gear Type Filter */}
        <div style={{ marginBottom: '24px' }}>
          <label style={{ textTransform: 'capitalize', display: 'block', marginBottom: '4px', fontWeight: 500, fontSize: '15px' }}>Gear Type:</label>
          <div>
            {gearTypes.map(type => (
              <label
                key={type.value}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  marginBottom: '6px',
                  cursor: 'pointer',
                  fontWeight: filters.gear_type === type.value ? 600 : 400,
                  color: filters.gear_type === type.value ? '#1a73e8' : '#000'
                }}
              >
                <input
                  type="checkbox"
                  checked={filters.gear_type === type.value}
                  onChange={() => handleCheckboxFilterClick('gear_type', type.value)}
                  style={{ marginRight: '8px', accentColor: '#1a73e8' }}
                />
                {type.label}
              </label>
            ))}
            {filters.gear_type && (
              <a
                href="#!"
                onClick={e => {
                  e.preventDefault();
                  handleCheckboxFilterClick('gear_type', '');
                }}
                style={{ display: 'block', marginTop: '8px', color: 'red', cursor: 'pointer', fontSize: '13px' }}
              >
                Clear gear type filter
              </a>
            )}
          </div>
        </div>
        {/* Brand Filter */}
        <div style={{ marginBottom: '24px' }}>
          <label style={{ textTransform: 'capitalize', display: 'block', marginBottom: '4px', fontWeight: 500, fontSize: '15px' }}>Brand:</label>
          <div>
            {brands.map(type => (
              <label
                key={type.value}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  marginBottom: '6px',
                  cursor: 'pointer',
                  fontWeight: filters.brand === type.value ? 600 : 400,
                  color: filters.brand === type.value ? '#1a73e8' : '#000'
                }}
              >
                <input
                  type="checkbox"
                  checked={filters.brand === type.value}
                  onChange={() => handleCheckboxFilterClick('brand', type.value)}
                  style={{ marginRight: '8px', accentColor: '#1a73e8' }}
                />
                {type.label}
              </label>
            ))}
            {filters.brand && (
              <a
                href="#!"
                onClick={e => {
                  e.preventDefault();
                  handleCheckboxFilterClick('brand', '');
                }}
                style={{ display: 'block', marginTop: '8px', color: 'red', cursor: 'pointer', fontSize: '13px' }}
              >
                Clear brand filter
              </a>
            )}
          </div>
        </div>
        {/* Year Filter */}
        <div style={{ marginBottom: '24px' }}>
          <label style={{ textTransform: 'capitalize', display: 'block', marginBottom: '4px', fontWeight: 500, fontSize: '15px' }}>Year:</label>
          <div>
            {years.map(type => (
              <label
                key={type.value}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  marginBottom: '6px',
                  cursor: 'pointer',
                  fontWeight: filters.year === type.value ? 600 : 400,
                  color: filters.year === type.value ? '#1a73e8' : '#000'
                }}
              >
                <input
                  type="checkbox"
                  checked={filters.year === type.value}
                  onChange={() => handleCheckboxFilterClick('year', type.value)}
                  style={{ marginRight: '8px', accentColor: '#1a73e8' }}
                />
                {type.label}
              </label>
            ))}
            {filters.year && (
              <a
                href="#!"
                onClick={e => {
                  e.preventDefault();
                  handleCheckboxFilterClick('year', '');
                }}
                style={{ display: 'block', marginTop: '8px', color: 'red', cursor: 'pointer', fontSize: '13px' }}
              >
                Clear year filter
              </a>
            )}
          </div>
        </div>
      </aside>

      <main style={containerStyle}>
        <div style={{ paddingTop: '85px', maxWidth: '1200px', margin: '0 auto' }}>
          <h2 style={{
            fontFamily: 'Amazon Ember, Arial, sans-serif',
            fontWeight: 700,
            fontSize: '1.5rem',
            marginBottom: '15px',
            color: '#222'
          }}>
            Car List
          </h2>
          {cars.length === 0 ? (
            <p style={{ fontFamily: 'Amazon Ember, Arial, sans-serif', color: '#555', fontSize: '1.15rem' }}>No cars available.</p>
          ) : (
            <>
              <div style={{ overflowX: 'auto', borderRadius: '16px', boxShadow: '0 2px 16px 0 rgba(40,116,240,0.07)' }}>
                <table style={tableStyle}>
                  <thead>
                    <tr style={{ background: '#f6f7fa' }}>
                      <th style={thTdStyle}>Description</th>
                      <th style={thTdStyle}>Year</th>
                      <th style={thTdStyle}>Location</th>
                      <th style={thTdStyle}>Mileage (km)</th>
                      <th style={thTdStyle}>Price (USD)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayedCars.map((car, idx) => (
                      <tr key={idx} style={{
                        background: idx % 2 === 0 ? '#fff' : '#f6f7fa',
                        transition: 'background 0.2s'
                      }}>
                        <td style={thTdStyle}>{car.description}</td>
                        <td style={thTdStyle}>{car.year}</td>
                        <td style={thTdStyle}>{car.location}</td>
                        <td style={thTdStyle}>{car.mileage}</td>
                        <td style={thTdStyle}>{car.price}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div style={paginationStyle}>
                <button
                  onClick={() => setCurrentPage(p => Math.max(p - 1, 1))}
                  disabled={currentPage === 1}
                  style={{
                    padding: '7px 18px',
                    borderRadius: '8px',
                    border: '1px solid #d5d9d9',
                    background: currentPage === 1 ? '#f5f6f6' : 'linear-gradient(180deg,#f7dfa5,#f0c14b)',
                    color: currentPage === 1 ? '#888' : '#111',
                    fontWeight: 500,
                    fontSize: '15px',
                    cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                    boxShadow: currentPage === 1 ? 'none' : '0 1px 0 #e2e2e2',
                    transition: 'background 0.2s, box-shadow 0.2s'
                  }}
                  onMouseOver={e => {
                    if (currentPage !== 1) {
                      e.currentTarget.style.background = 'linear-gradient(180deg,#f0c14b,#e7b13b)';
                    }
                  }}
                  onMouseOut={e => {
                    if (currentPage !== 1) {
                      e.currentTarget.style.background = 'linear-gradient(180deg,#f7dfa5,#f0c14b)';
                    }
                  }}
                >
                  Previous
                </button>
                <span
                  style={{
                    padding: '7px 18px',
                    borderRadius: '8px',
                    border: '1px solid #d5d9d9',
                    background: '#fff',
                    color: '#111',
                    fontWeight: 600,
                    fontSize: '15px',
                    boxShadow: '0 1px 0 #e2e2e2',
                    minWidth: '110px',
                    textAlign: 'center',
                    letterSpacing: '0.5px'
                  }}
                >
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(p => Math.min(p + 1, totalPages))}
                  disabled={currentPage === totalPages}
                  style={{
                    padding: '7px 18px',
                    borderRadius: '8px',
                    border: '1px solid #d5d9d9',
                    background: currentPage === totalPages ? '#f5f6f6' : 'linear-gradient(180deg,#f7dfa5,#f0c14b)',
                    color: currentPage === totalPages ? '#888' : '#111',
                    fontWeight: 500,
                    fontSize: '15px',
                    cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                    boxShadow: currentPage === totalPages ? 'none' : '0 1px 0 #e2e2e2',
                    transition: 'background 0.2s, box-shadow 0.2s'
                  }}
                  onMouseOver={e => {
                    if (currentPage !== totalPages) {
                      e.currentTarget.style.background = 'linear-gradient(180deg,#f0c14b,#e7b13b)';
                    }
                  }}
                  onMouseOut={e => {
                    if (currentPage !== totalPages) {
                      e.currentTarget.style.background = 'linear-gradient(180deg,#f7dfa5,#f0c14b)';
                    }
                  }}
                >
                  Next
                </button>
              </div>
            </>
          )}
        </div>
      </main>
    </>
  );
}

export default CarList;
