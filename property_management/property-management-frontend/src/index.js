import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom"; // ✅ Only declare here
import { MyContextProvider } from "./context/MyContext"; 
import App from "./App";
import "./index.css";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <MyContextProvider>
      <BrowserRouter> {/* ✅ BrowserRouter should only be used here */}
        <App />
      </BrowserRouter>
    </MyContextProvider>
  </React.StrictMode>
);
