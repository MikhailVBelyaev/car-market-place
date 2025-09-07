import React, { useState, useEffect } from 'react';

const API_URL = '/api/cars/filtered-list/';

const CarList = ({ onSearch }) => {
  const [cars, setCars] = useState([]);
  const [filterConfig, setFilterConfig] = useState({});
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
    mileage: '',
    created_at: '',
  });
  const [currentPage, setCurrentPage] = useState(1);
  const [error, setError] = useState(null);
  const rowsPerPage = 10;

  const getDateFilter = (type) => {
    const today = new Date();
    const todayUTC = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
    const yyyy = todayUTC.getUTCFullYear();
    const mm = String(todayUTC.getUTCMonth() + 1).padStart(2, '0');
    const dd = String(todayUTC.getUTCDate()).padStart(2, '0');
    const todayStr = `${yyyy}-${mm}-${dd}`;

    if (type === 'today') return todayStr;
    if (type === 'last3days') {
      const last3Days = new Date(todayUTC);
      last3Days.setUTCDate(todayUTC.getUTCDate() - 3);
      return `${last3Days.getUTCFullYear()}-${String(last3Days.getUTCMonth() + 1).padStart(2, '0')}-${String(last3Days.getUTCDate()).padStart(2, '0')}-${todayStr}`;
    }
    if (type === 'lastweek') {
      const lastWeek = new Date(todayUTC);
      lastWeek.setUTCDate(todayUTC.getUTCDate() - 7);
      return `${lastWeek.getUTCFullYear()}-${String(lastWeek.getUTCMonth() + 1).padStart(2, '0')}-${String(lastWeek.getUTCDate()).padStart(2, '0')}-${todayStr}`;
    }
    if (type === 'lastmonth') {
      const lastMonth = new Date(todayUTC);
      lastMonth.setUTCDate(todayUTC.getUTCDate() - 30);
      return `${lastMonth.getUTCFullYear()}-${String(lastMonth.getUTCMonth() + 1).padStart(2, '0')}-${String(lastMonth.getUTCDate()).padStart(2, '0')}-${todayStr}`;
    }
    return '';
  };

  const fetchCars = (queryParams = '', customFilters = null) => {
    const query = new URLSearchParams(queryParams);
    const usedFilters = customFilters || filters;
    for (const key in usedFilters) {
      if (usedFilters[key] && key !== 'model') query.append(key, usedFilters[key]);
    }
    if (usedFilters.model) query.append('model', usedFilters.model);
    console.log(`Fetching cars with query: ${query.toString()}`);
    fetch(`${API_URL}?${query.toString()}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        console.log('Fetched cars:', data.results);
        console.log('Filter Config:', data.filters);
        setCars(data.results || []);
        setFilterConfig(data.filters || {});
        setError(null);
        setCurrentPage(1);
      })
      .catch((err) => {
        console.error('Error fetching cars:', err);
        setError('Failed to load cars. Please try again.');
        setCars([]);
      });
  };

  useEffect(() => {
    fetchCars();
  }, []);

  useEffect(() => {
    fetchCars();
  }, [
    filters.fuel_type,
    filters.gear_type,
    filters.color,
    filters.vehicle_type,
    filters.condition,
    filters.brand,
    filters.year,
    filters.price,
    filters.mileage,
    filters.created_at,
  ]);

  useEffect(() => {
    if (onSearch !== undefined) {
      setFilters((prev) => ({ ...prev, model: onSearch || '' }));
    }
  }, [onSearch]);

  const handleCheckboxFilterClick = (filterKey, value) => {
    const newValue = filters[filterKey] === value ? '' : value;
    setFilters((prevFilters) => ({ ...prevFilters, [filterKey]: newValue }));
    setCurrentPage(1);
  };

  const handleDropdownFilterChange = (filterKey, e) => {
    const value = e.target.value;
    setFilters((prevFilters) => ({ ...prevFilters, [filterKey]: value }));
    setCurrentPage(1);
  };

  const handleDateFilterClick = (type) => {
    const dateValue = getDateFilter(type);
    const updatedFilters = { ...filters, created_at: dateValue };
    setFilters(updatedFilters);
    setCurrentPage(1);
    // Immediately trigger fetchCars with the updated filters
    fetchCars('', updatedFilters);
  };

  const totalPages = Math.ceil(cars.length / rowsPerPage);
  const displayedCars = cars.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage);

  const sidebarStyle = {
    width: '250px',
    padding: '20px',
    borderRight: '1px solid #ccc',
    height: 'calc(100vh - 110px)',
    boxSizing: 'border-box',
    position: 'fixed',
    overflowY: 'auto',
    backgroundColor: '#f9f9f9',
    top: '110px', // Below header (68px) + menu (~42px)
    left: '0',
    zIndex: 100,
  };

  const containerStyle = {
    marginLeft: '270px',
    padding: '20px',
    minHeight: 'calc(100vh - 110px)',
    background: '#fff',
    boxSizing: 'border-box',
  };

  const tableContainerStyle = {
    maxWidth: '1200px', // Match old version
    margin: '0 auto',
    paddingTop: '20px', // Reduced from 85px to align with new header/menu
  };

  const tableStyle = {
    width: '100%',
    borderCollapse: 'separate',
    borderSpacing: '0',
    background: '#fff',
    borderRadius: '16px',
    overflow: 'hidden',
    boxShadow: '0 2px 16px 0 rgba(40,116,240,0.07)',
    margin: '0 0 20px 0',
  };

  const thTdStyle = {
    borderBottom: '1px solid #eee',
    padding: '14px 12px',
    textAlign: 'left',
    fontSize: '16px',
    fontFamily: 'Amazon Ember, Arial, sans-serif',
  };

  const paginationStyle = {
    marginTop: '15px',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '12px',
    fontFamily: 'Amazon Ember, Arial, sans-serif',
  };

  const selectStyle = {
    width: '100%',
    padding: '6px',
    boxSizing: 'border-box',
    fontFamily: 'Amazon Ember, Arial, sans-serif',
    fontWeight: 500,
    fontSize: '15px',
    borderRadius: '4px',
    border: '1px solid #ccc',
    backgroundColor: '#fff',
    cursor: 'pointer',
  };

  const dateFilterButtonStyle = {
    padding: '10px 20px',
    cursor: 'pointer',
    fontWeight: 600,
    background: 'linear-gradient(90deg, #2874f0 0%, #0057b8 100%)',
    color: '#fff',
    border: 'none',
    borderRadius: '20px',
    boxShadow: '0 2px 6px 0 rgba(40,116,240,0.15)',
    fontSize: '15px',
    letterSpacing: '0.5px',
    transition: 'background 0.2s, box-shadow 0.2s, transform 0.1s',
    marginRight: '8px',
    marginBottom: '8px',
  };

  const dateFilterButtonHoverStyle = {
    background: 'linear-gradient(90deg, #0057b8 0%, #2874f0 100%)',
    boxShadow: '0 4px 16px 0 rgba(40,116,240,0.25)',
    transform: 'translateY(-2px) scale(1.03)',
  };

  const cleanButtonStyle = {
    padding: '10px 20px',
    cursor: 'pointer',
    background: 'linear-gradient(90deg, #ff5a36 0%, #c62828 100%)',
    color: '#fff',
    border: 'none',
    borderRadius: '20px',
    fontWeight: 600,
    fontSize: '15px',
    letterSpacing: '0.5px',
    boxShadow: '0 2px 6px 0 rgba(255,90,54,0.13)',
    transition: 'background 0.2s, box-shadow 0.2s, transform 0.1s',
    marginRight: '8px',
    marginBottom: '8px',
  };

  const cleanButtonHoverStyle = {
    background: 'linear-gradient(90deg, #c62828 0%, #ff5a36 100%)',
    boxShadow: '0 4px 16px 0 rgba(255,90,54,0.22)',
    transform: 'translateY(-2px) scale(1.03)',
  };

  return (
    <div>
      <style>
        {`
          @media (max-width: 768px) {
            aside {
              width: 100% !important;
              position: relative !important;
              height: auto !important;
              top: 0 !important;
              padding-top: 10px !important;
            }
            main {
              margin-left: 0 !important;
              padding: 10px !important;
            }
            div[style*="maxWidth: 1200px"] {
              max-width: 100% !important;
              padding-top: 10px !important;
            }
            table {
              font-size: 14px !important;
            }
            th, td {
              padding: 10px 8px !important;
            }
            select {
              font-size: 14px !important;
            }
            button {
              font-size: 14px !important;
              padding: 8px 16px !important;
            }
          }
        `}
      </style>
      <aside style={sidebarStyle}>
        <h2 style={{ fontFamily: 'Amazon Ember, Arial, sans-serif', fontWeight: 800, fontSize: '1.4rem', margin: '0 0 15px' }}>
          Filters
        </h2>
        <div style={{ display: 'flex', gap: '12px', marginBottom: '22px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            onClick={() => fetchCars()}
            style={dateFilterButtonStyle}
            onMouseOver={(e) => Object.assign(e.currentTarget.style, dateFilterButtonHoverStyle)}
            onMouseOut={(e) => Object.assign(e.currentTarget.style, dateFilterButtonStyle)}
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
                mileage: '',
                created_at: '',
              });
              setCurrentPage(1);
              setTimeout(() => fetchCars(), 0);
            }}
            style={cleanButtonStyle}
            onMouseOver={(e) => Object.assign(e.currentTarget.style, cleanButtonHoverStyle)}
            onMouseOut={(e) => Object.assign(e.currentTarget.style, cleanButtonStyle)}
          >
            Clear All Filters
          </button>
        </div>
        {Object.keys(filterConfig).length === 0 ? (
          <p style={{ fontFamily: 'Amazon Ember, Arial, sans-serif', color: '#555', fontSize: '16px' }}>
            Loading filters...
          </p>
        ) : (
          Object.entries(filterConfig).map(([key, config]) => (
            <div key={key} style={{ marginBottom: '24px' }}>
              <label
                style={{
                  textTransform: 'capitalize',
                  display: 'block',
                  marginBottom: '6px',
                  fontWeight: 500,
                  fontSize: '15px',
                  whiteSpace: 'nowrap',
                }}
              >
                {key.replace('_', ' ')}:
              </label>
              {config.type === 'checkbox' ? (
                <div>
                  {config.options.map((option) => (
                    <label
                      key={option.value}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        marginBottom: '8px',
                        cursor: 'pointer',
                        fontWeight: filters[key] === option.value ? 600 : 400,
                        color: filters[key] === option.value ? '#1a73e8' : '#000',
                        fontFamily: 'Amazon Ember, Arial, sans-serif',
                        fontSize: '15px',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={filters[key] === option.value}
                        onChange={() => handleCheckboxFilterClick(key, option.value)}
                        style={{ marginRight: '10px', accentColor: '#1a73e8' }}
                      />
                      {option.label} ({option.count})
                    </label>
                  ))}
                  {filters[key] && (
                    <a
                      href="#!"
                      onClick={(e) => {
                        e.preventDefault();
                        handleCheckboxFilterClick(key, '');
                      }}
                      style={{ display: 'block', marginTop: '8px', color: 'red', cursor: 'pointer', fontSize: '14px', whiteSpace: 'nowrap' }}
                    >
                      Clear {key.replace('_', ' ')} filter
                    </a>
                  )}
                </div>
              ) : (
                <div>
                  <select
                    value={filters[key] || ''}
                    onChange={(e) => handleDropdownFilterChange(key, e)}
                    style={selectStyle}
                  >
                    <option value="">Select {key.replace('_', ' ')}</option>
                    {config.options.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label} ({option.count})
                      </option>
                    ))}
                  </select>
                  {filters[key] && (
                    <a
                      href="#!"
                      onClick={(e) => {
                        e.preventDefault();
                        handleDropdownFilterChange(key, { target: { value: '' } });
                      }}
                      style={{ display: 'block', marginTop: '8px', color: 'red', cursor: 'pointer', fontSize: '14px', whiteSpace: 'nowrap' }}
                    >
                      Clear {key.replace('_', ' ')} filter
                    </a>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </aside>
      <main style={containerStyle}>
        <div style={tableContainerStyle}>
          <h2
            style={{
              fontFamily: 'Amazon Ember, Arial, sans-serif',
              fontWeight: 700,
              fontSize: '1.6rem',
              margin: '0 0 15px',
              color: '#222',
            }}
          >
            Car List
          </h2>
          {error && (
            <p
              style={{
                fontFamily: 'Amazon Ember, Arial, sans-serif',
                color: 'red',
                fontSize: '1.15rem',
                marginBottom: '20px',
              }}
            >
              {error}
            </p>
          )}
          <div style={{ marginBottom: '20px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            <button
              onClick={() => handleDateFilterClick('today')}
              style={{
                ...dateFilterButtonStyle,
                background:
                  filters.created_at === getDateFilter('today')
                    ? 'linear-gradient(90deg, #0057b8 0%, #2874f0 100%)'
                    : dateFilterButtonStyle.background,
              }}
              onMouseOver={(e) => Object.assign(e.currentTarget.style, dateFilterButtonHoverStyle)}
              onMouseOut={(e) => {
                e.currentTarget.style.background =
                  filters.created_at === getDateFilter('today')
                    ? 'linear-gradient(90deg, #0057b8 0%, #2874f0 100%)'
                    : dateFilterButtonStyle.background;
                e.currentTarget.style.boxShadow = dateFilterButtonStyle.boxShadow;
                e.currentTarget.style.transform = '';
              }}
            >
              Today
            </button>
            <button
              onClick={() => handleDateFilterClick('last3days')}
              style={{
                ...dateFilterButtonStyle,
                background:
                  filters.created_at === getDateFilter('last3days')
                    ? 'linear-gradient(90deg, #0057b8 0%, #2874f0 100%)'
                    : dateFilterButtonStyle.background,
              }}
              onMouseOver={(e) => Object.assign(e.currentTarget.style, dateFilterButtonHoverStyle)}
              onMouseOut={(e) => {
                e.currentTarget.style.background =
                  filters.created_at === getDateFilter('last3days')
                    ? 'linear-gradient(90deg, #0057b8 0%, #2874f0 100%)'
                    : dateFilterButtonStyle.background;
                e.currentTarget.style.boxShadow = dateFilterButtonStyle.boxShadow;
                e.currentTarget.style.transform = '';
              }}
            >
              Last 3 Days
            </button>
            <button
              onClick={() => handleDateFilterClick('lastweek')}
              style={{
                ...dateFilterButtonStyle,
                background:
                  filters.created_at === getDateFilter('lastweek')
                    ? 'linear-gradient(90deg, #0057b8 0%, #2874f0 100%)'
                    : dateFilterButtonStyle.background,
              }}
              onMouseOver={(e) => Object.assign(e.currentTarget.style, dateFilterButtonHoverStyle)}
              onMouseOut={(e) => {
                e.currentTarget.style.background =
                  filters.created_at === getDateFilter('lastweek')
                    ? 'linear-gradient(90deg, #0057b8 0%, #2874f0 100%)'
                    : dateFilterButtonStyle.background;
                e.currentTarget.style.boxShadow = dateFilterButtonStyle.boxShadow;
                e.currentTarget.style.transform = '';
              }}
            >
              Last Week
            </button>
            <button
              onClick={() => handleDateFilterClick('lastmonth')}
              style={{
                ...dateFilterButtonStyle,
                background:
                  filters.created_at === getDateFilter('lastmonth')
                    ? 'linear-gradient(90deg, #0057b8 0%, #2874f0 100%)'
                    : dateFilterButtonStyle.background,
              }}
              onMouseOver={(e) => Object.assign(e.currentTarget.style, dateFilterButtonHoverStyle)}
              onMouseOut={(e) => {
                e.currentTarget.style.background =
                  filters.created_at === getDateFilter('lastmonth')
                    ? 'linear-gradient(90deg, #0057b8 0%, #2874f0 100%)'
                    : dateFilterButtonStyle.background;
                e.currentTarget.style.boxShadow = dateFilterButtonStyle.boxShadow;
                e.currentTarget.style.transform = '';
              }}
            >
              Last Month
            </button>
            <button
              onClick={() => handleDateFilterClick('clean')}
              style={cleanButtonStyle}
              onMouseOver={(e) => Object.assign(e.currentTarget.style, cleanButtonHoverStyle)}
              onMouseOut={(e) => Object.assign(e.currentTarget.style, cleanButtonStyle)}
            >
              Clean
            </button>
          </div>
          {cars.length === 0 && !error ? (
            <p style={{ fontFamily: 'Amazon Ember, Arial, sans-serif', color: '#555', fontSize: '1.15rem' }}>
              No cars available.
            </p>
          ) : (
            <>
              <div style={{ overflowX: 'auto' }}>
                <table style={tableStyle}>
                  <thead>
                    <tr style={{ background: '#f6f7fa' }}>
                      <th style={thTdStyle}>Description</th>
                      <th style={thTdStyle}>Year</th>
                      <th style={thTdStyle}>Location</th>
                      <th style={thTdStyle}>Mileage (km)</th>
                      <th style={thTdStyle}>Price (USD)</th>
                      <th style={thTdStyle}>Link</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayedCars.map((car, idx) => (
                      <tr
                        key={idx}
                        style={{
                          background: idx % 2 === 0 ? '#fff' : '#f6f7fa',
                          transition: 'background 0.2s',
                        }}
                      >
                        <td style={thTdStyle}>{car.description || 'N/A'}</td>
                        <td style={thTdStyle}>{car.year || 'N/A'}</td>
                        <td style={thTdStyle}>{car.location || 'N/A'}</td>
                        <td style={thTdStyle}>{car.mileage || 'N/A'}</td>
                        <td style={thTdStyle}>{car.price || 'N/A'}</td>
                        <td style={thTdStyle}>
                          {car.reference_url ? (
                            <a
                              href={car.reference_url}
                              target="_blank"
                              rel="noopener noreferrer"
                            >
                              Open
                            </a>
                          ) : (
                            'N/A'
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div style={paginationStyle}>
                <button
                  onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
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
                    transition: 'background 0.2s, box-shadow 0.2s',
                  }}
                  onMouseOver={(e) => {
                    if (currentPage !== 1) {
                      e.currentTarget.style.background = 'linear-gradient(180deg,#f0c14b,#e7b13b)';
                    }
                  }}
                  onMouseOut={(e) => {
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
                    letterSpacing: '0.5px',
                  }}
                >
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))}
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
                    transition: 'background 0.2s, box-shadow 0.2s',
                  }}
                  onMouseOver={(e) => {
                    if (currentPage !== totalPages) {
                      e.currentTarget.style.background = 'linear-gradient(180deg,#f0c14b,#e7b13b)';
                    }
                  }}
                  onMouseOut={(e) => {
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
    </div>
  );
};

export default CarList;