// App.jsx  —  Root application component
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar    from "./components/Navbar";
import Dashboard from "./pages/Dashboard";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-surface">
        <Navbar />
        <Routes>
          <Route path="/" element={<Dashboard />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
