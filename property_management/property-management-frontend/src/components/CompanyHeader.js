import React from "react";

const CompanyHeader = () => {
  const styles = {
    header: {
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      marginBottom: "20px",
      padding: "10px",
      borderBottom: "2px solid #ddd",
    },
    image: {
      maxWidth: "100px",
    },
    textContainer: {
      textAlign: "right",
    },
    text: {
      margin: "5px 0",
      color: "#555",
    },
  };

  return (
    <div style={styles.header}>
    <img src="/uploads/t.png" alt="Company Logo" />
      <div style={styles.textContainer}>
        <h2>Zuripo Property Specialists Ltd</h2>
        <p style={styles.text}>Garden Estate, Off Northern Bypass</p>
        <p style={styles.text}>Phone: 254 792 262 000</p>
        <p style={styles.text}>Email: info@zuripoproperties.co.ke</p>
      </div>
    </div>
  );
};

export default CompanyHeader;
