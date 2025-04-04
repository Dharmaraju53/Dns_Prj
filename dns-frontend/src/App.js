import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import Resolver from './pages/Resolver';
import About from './pages/About';

function App() {
  return (
    <Router>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/resolver" element={<Resolver />} />
        <Route path="/about" element={<About />} />
      </Routes>
    </Router>
  );
}

export default App;
