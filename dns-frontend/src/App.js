import React, { useState } from "react";

function App() {
    const [domain, setDomain] = useState("");
    const [protocol, setProtocol] = useState("udp");
    const [response, setResponse] = useState("");
    const [loading, setLoading] = useState(false);

    const handleResolve = async () => {
        setLoading(true);
        setResponse("");

        try {
            const res = await fetch(`http://localhost:8000/resolve?domain=${domain}&protocol=${protocol}`, {
                method: "GET",
                headers: { "Content-Type": "application/json" }
            });

            if (!res.ok) {
                throw new Error("Failed to fetch data from backend");
            }

            const data = await res.json();
            setResponse(data.response || "Error resolving domain.");
        } catch (error) {
            console.error("Fetch error:", error);
            setResponse("Error fetching DNS data. Check backend.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={styles.container}>
            <h1 style={styles.heading}>DNS Resolver</h1>
            <p style={styles.subtitle}>Enter a domain and select a protocol to resolve its IP.</p>

            <div style={styles.inputContainer}>
                <input 
                    type="text" 
                    value={domain} 
                    onChange={(e) => setDomain(e.target.value)} 
                    placeholder="Enter domain name" 
                    style={styles.input}
                />

                <select 
                    value={protocol} 
                    onChange={(e) => setProtocol(e.target.value)} 
                    style={styles.select}
                >
                    <option value="udp">UDP</option>
                    <option value="tcp">TCP</option>
                </select>

                <button 
                    onClick={handleResolve} 
                    disabled={loading || !domain.trim()} 
                    style={styles.button}
                >
                    {loading ? "Resolving..." : "Resolve"}
                </button>
            </div>

            {response && (
                <div style={styles.responseBox}>
                    <h3 style={styles.responseTitle}>🔍 Query Log</h3>
                    <div style={styles.logEntry}>✅ <b>Query Sent:</b> {domain} ({protocol.toUpperCase()})</div>
                    <div style={styles.logEntry}>📡 <b>Resolver IP:</b> 192.168.0.155:9292</div>

                    <h3 style={styles.responseTitle}>📨 Server Response</h3>
                    <div style={styles.logEntry}>🔐 <b>Encrypted Data:</b></div>
                    <pre style={styles.rawLog}>{response.split("\n")[1]}</pre>

                    <div style={styles.logEntry}>🔓 <b>Decrypted Data:</b></div>
                    <pre style={styles.finalResponse}>{response.split("\n")[2]}</pre>
                </div>
            )}
        </div>
    );
}

// ✅ New Stylish UI Design (Better Logs)
const styles = {
    container: {
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100vh",
        background: "linear-gradient(to right, #141e30, #243b55)",
        fontFamily: "Arial, sans-serif",
        color: "#ffffff",
        textAlign: "center",
    },
    heading: {
        fontSize: "2.5rem",
        fontWeight: "bold",
        marginBottom: "10px",
        textShadow: "2px 2px 5px rgba(0, 0, 0, 0.5)",
    },
    subtitle: {
        fontSize: "1rem",
        opacity: 0.8,
        marginBottom: "20px",
    },
    inputContainer: {
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(255, 255, 255, 0.1)",
        padding: "15px",
        borderRadius: "12px",
        backdropFilter: "blur(10px)",
        boxShadow: "0px 0px 15px rgba(255, 255, 255, 0.1)",
    },
    input: {
        padding: "12px",
        borderRadius: "8px",
        border: "none",
        outline: "none",
        fontSize: "1rem",
        width: "250px",
        marginRight: "10px",
        background: "rgba(255, 255, 255, 0.2)",
        color: "#ffffff",
        textAlign: "center",
    },
    select: {
        padding: "12px",
        borderRadius: "8px",
        border: "none",
        outline: "none",
        fontSize: "1rem",
        marginRight: "10px",
        cursor: "pointer",
        background: "rgba(255, 255, 255, 0.2)",
        color: "#ffffff",
    },
    button: {
        padding: "12px 20px",
        borderRadius: "8px",
        border: "none",
        fontSize: "1rem",
        cursor: "pointer",
        backgroundColor: "#007bff",
        color: "#ffffff",
        transition: "0.3s",
    },
    responseBox: {
        marginTop: "20px",
        padding: "15px",
        width: "60%",
        borderRadius: "12px",
        background: "rgba(255, 255, 255, 0.1)",
        backdropFilter: "blur(10px)",
        boxShadow: "0px 0px 15px rgba(255, 255, 255, 0.1)",
        textAlign: "left",
    },
    responseTitle: {
        fontSize: "1.2rem",
        fontWeight: "bold",
        marginBottom: "5px",
        color: "#ffcc00",
    },
    logEntry: {
        fontSize: "1rem",
        marginBottom: "5px",
    },
    rawLog: {
        fontSize: "0.9rem",
        padding: "10px",
        background: "#333",
        color: "#f1c40f",
        borderRadius: "8px",
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
    },
    finalResponse: {
        fontSize: "1.1rem",
        padding: "10px",
        background: "#222",
        color: "#2ecc71",
        borderRadius: "8px",
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
    },
};

export default App;
