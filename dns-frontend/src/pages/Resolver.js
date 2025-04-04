import React, { useState } from 'react';

function Resolver() {
  const [domain, setDomain] = useState('');
  const [result, setResult] = useState('');

  const resolveDomain = async () => {
    try {
      const response = await fetch('https://dns.google/resolve?name=' + domain);
      const data = await response.json();
      if (data.Answer) {
        const ips = data.Answer.map(ans => ans.data).join(', ');
        setResult('Resolved IP(s): ' + ips);
      } else {
        setResult('Could not resolve domain.');
      }
    } catch (err) {
      setResult('Error resolving domain.');
    }
  };

  return (
    <div className="container">
      <h2>DNS Resolver Tool</h2>
      <input type="text" placeholder="Enter domain (e.g., example.com)" value={domain} onChange={e => setDomain(e.target.value)} />
      <button onClick={resolveDomain}>Resolve</button>
      <p>{result}</p>
    </div>
  );
}

export default Resolver;
