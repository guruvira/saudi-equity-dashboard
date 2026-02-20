import React, { useEffect } from 'react';
import { Dashboard } from './components/Dashboard';
import { Toaster } from './components/ui/sonner';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  useEffect(() => {
    // Seed data on app load
    const seedData = async () => {
      try {
        await axios.post(`${API}/seed-data`);
      } catch (error) {
        console.log('Data already seeded or error:', error.message);
      }
    };
    seedData();
  }, []);

  return (
    <div className="App">
      <Dashboard />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#1e293b',
            color: '#f8fafc',
            border: '1px solid rgba(212, 175, 55, 0.3)'
          }
        }}
      />
    </div>
  );
}

export default App;
