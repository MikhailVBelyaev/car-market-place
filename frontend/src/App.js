import React, { useState, useEffect } from "react";

function App() {
  const [cars, setCars] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch data from Django backend
    fetch("http://127.0.0.1:8000/api/cars/")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to fetch cars");
        }
        return response.json();
      })
      .then((data) => {
        setCars(data);
        setLoading(false);
      })
      .catch((error) => {
        console.error("Error fetching data:", error);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <p>Loading...</p>;
  }

  return (
    <div>
      <h1>Car List</h1>
      {cars.length > 0 ? (
        <table border="1" style={{ borderCollapse: "collapse", width: "100%" }}>
        <thead>
          <tr>
            <th>Date</th>
            <th>Brand</th>
            <th>Model</th>
            <th>Year</th>
            <th>Mileage (km)</th>
            <th>Price ($)</th>
            <th style={{ 
                maxWidth: "300px", 
                overflow: "hidden", 
                textOverflow: "ellipsis", 
                whiteSpace: "nowrap" 
                }}>Description</th>
          </tr>
        </thead>
        <tbody>
          {cars.map((car) => (
            <tr key={car.id}>
              <td>{new Date(car.created_at).toISOString().split("T")[0]}</td>
              <td>{car.brand}</td>
              <td>{car.model}</td>
              <td>{car.year}</td>
              <td>{car.mileage}</td>
              <td>{car.price}</td>
              <td style={{ 
                maxWidth: "300px", 
                overflow: "hidden", 
                textOverflow: "ellipsis", 
                whiteSpace: "nowrap" 
                }}>{car.description}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      ) : (
        <p>No cars available.</p>
      )}
    </div>
  );
}

export default App;