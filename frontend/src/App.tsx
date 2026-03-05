import { Routes, Route } from 'react-router-dom'
import './App.css'

function Home() {
  return (
    <main className="main">
      <h1>CronosMatic</h1>
      <p>Welcome to CronosMatic</p>
    </main>
  )
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
    </Routes>
  )
}

export default App
