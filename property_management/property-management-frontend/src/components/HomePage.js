import React from "react";
import { Link } from "react-router-dom";

const HomePage = () => {
  return (
    <div className="container">
      <h1>Welcome to the Property Management System</h1>
      <p>Manage properties, tenants, and transactions with ease.</p>
      <Link to="/dashboard">
        <button>Go to Dashboard</button>
      </Link>
    </div>
  );
};

export default HomePage;
