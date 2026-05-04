import { Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import StockDetail from "./pages/StockDetail.jsx";
import Prediction from "./pages/Prediction.jsx";
import News from "./pages/News.jsx";

export default function App() {
  return (
    <div className="min-h-screen bg-soft text-ink">
      <Navbar />
      <main className="container-width pb-16 pt-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/stocks" element={<StockDetail />} />
          <Route path="/prediction" element={<Prediction />} />
          <Route path="/news" element={<News />} />
        </Routes>
      </main>
    </div>
  );
}
