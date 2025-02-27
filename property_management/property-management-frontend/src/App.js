import React from "react";
import Navbar from "./components/Navbar";
import AppRoutes from "./Routes"; // ✅ Ensure correct import
import CompanyHeader from "./components/CompanyHeader";

function App() {
  return (
    <div>
      <CompanyHeader />  {/* Add the Company Header here */}
      <Navbar />
      <AppRoutes />
    </div>
  );
}

export default App;
