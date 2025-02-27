import { useState } from "react";
import axios from "axios";

export default function AddProperty() {
  const [property, setProperty] = useState({ name: "", address: "", owner_id: "" });
  const [message, setMessage] = useState("");

  const handleChange = (e) => {
    setProperty({ ...property, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!property.name || !property.address || !property.owner_id) {
      setMessage("All fields are required.");
      return;
    }
    try {
      const response = await axios.post("http://127.0.0.1:5000/properties", property);
      setMessage("Property added successfully!");
      setProperty({ name: "", address: "", owner_id: "" });
    } catch (error) {
      setMessage("Error adding property.");
    }
  };

  return (
    <div className="max-w-md mx-auto mt-10 p-6 bg-white shadow-lg rounded-xl">
      <h2 className="text-2xl font-bold mb-4">Add Property</h2>
      {message && <p className="text-red-500 mb-4">{message}</p>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="text"
          name="name"
          placeholder="Property Name"
          value={property.name}
          onChange={handleChange}
          className="w-full p-2 border border-gray-300 rounded"
        />
        <input
          type="text"
          name="address"
          placeholder="Property Address"
          value={property.address}
          onChange={handleChange}
          className="w-full p-2 border border-gray-300 rounded"
        />
        <input
          type="number"
          name="owner_id"
          placeholder="Owner ID"
          value={property.owner_id}
          onChange={handleChange}
          className="w-full p-2 border border-gray-300 rounded"
        />
        <button type="submit" className="w-full bg-blue-500 text-white py-2 rounded">
          Add Property
        </button>
      </form>
    </div>
  );
}
