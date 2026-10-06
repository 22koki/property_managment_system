import axios from "axios";

const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL || "http://127.0.0.1:5000";

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

export const getProperties = async () => {
  const response = await api.get("/properties");
  return response.data;
};

export const getTenants = async () => {
  const response = await api.get("/tenants");
  return response.data;
};

export const addProperty = async (propertyData) => {
  const response = await api.post("/properties", propertyData);
  return response.data;
};

export const getUnits = async () => {
  const response = await api.get("/units");
  return response.data;
};

export const getInvoices = async () => {
  const response = await api.get("/invoices");
  return response.data;
};

export const createReceipt = async (receiptData) => {
  const response = await api.post("/receipts", receiptData);
  return response.data;
};

export const getMaintenanceRequests = async () => {
  const response = await api.get("/maintenance_requests");
  return response.data;
};

export const createMaintenanceRequest = async (payload) => {
  const response = await api.post("/maintenance_requests", payload);
  return response.data;
};

export default api;
