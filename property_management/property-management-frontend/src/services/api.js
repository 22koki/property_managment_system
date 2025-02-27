import axios from "axios";

const API_BASE_URL = "http://127.0.0.1:5000"; // Your Flask backend

export const getProperties = async () => {
  const response = await axios.get(`${API_BASE_URL}/properties`);
  return response.data;
};

export const getTenants = async () => {
  const response = await axios.get(`${API_BASE_URL}/tenants`);
  return response.data;
};

export const addProperty = async (propertyData) => {
  const response = await axios.post(`${API_BASE_URL}/properties`, propertyData);
  return response.data;
};
