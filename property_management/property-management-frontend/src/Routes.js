import React from "react";
import { Routes, Route } from "react-router-dom"; // ✅ Do NOT import BrowserRouter here
import HomePage from "./components/HomePage";
import Dashboard from "./components/Dashboard";

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/dashboard" element={<Dashboard />} />
    </Routes>
  );
};

export default AppRoutes;
