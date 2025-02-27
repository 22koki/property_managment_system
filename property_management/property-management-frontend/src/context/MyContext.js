import { createContext, useContext, useState } from "react";

// Create the context
const MyContext = createContext(null);

// Provider component
export const MyContextProvider = ({ children }) => {
  const [state, setState] = useState("default value");

  return (
    <MyContext.Provider value={{ state, setState }}>
      {children}
    </MyContext.Provider>
  );
};

// Custom hook to use the context
export const useMyContext = () => {
  const context = useContext(MyContext);
  if (!context) {
    throw new Error("useMyContext must be used within a MyContextProvider");
  }
  return context;
};
