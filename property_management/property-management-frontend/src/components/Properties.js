import { useState, useEffect } from "react";
import axios from "axios";

const Properties = () => {
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios.get("http://127.0.0.1:5000/properties")
      .then(response => {
        setProperties(response.data);
        setLoading(false);
      })
      .catch(err => {
        setError("Failed to load properties. Try again later.");
        setLoading(false);
      });
  }, []);

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <h1 className="text-3xl font-bold text-center text-blue-700 mb-6">Property Listings</h1>

      {loading && (
        <div className="text-center text-gray-600">Loading properties...</div>
      )}

      {error && (
        <div className="text-center text-red-500">{error}</div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {properties.map((property) => (
          <div key={property.property_id} className="bg-white p-4 rounded-2xl shadow-md hover:shadow-lg transition">
            <h2 className="text-xl font-semibold text-gray-800">{property.name}</h2>
            <p className="text-gray-600">{property.address}</p>
            <p className="text-sm text-gray-500 mt-2">Owner ID: {property.owner_id}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Properties;
