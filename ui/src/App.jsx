import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios.get('/api/agents')
      .then(response => {
        setAgents(response.data.agents || []);
        setLoading(false);
      })
      .catch(error => {
        console.error('Error fetching agents:', error);
        setLoading(false);
      });
  }, []);

  return (
    <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
      <h1>🔬 openScience</h1>
      <p>Open-source AI workbench for scientific research</p>
      <h2>Available Agents</h2>
      {loading ? (
        <p>Loading...</p>
      ) : (
        <ul>
          {agents.map(agent => (
            <li key={agent.name}>
              <strong>{agent.name}</strong> - {agent.description}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default App;
