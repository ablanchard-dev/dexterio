import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import Setups from "@/pages/Setups";
import Performance from "@/pages/Performance";
import Journal from "@/pages/Journal";
import MarketAnalysis from "@/pages/MarketAnalysis";
import RiskManagement from "@/pages/RiskManagement";
import Backtests from "@/pages/Backtests";

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/setups" element={<Setups />} />
            <Route path="/performance" element={<Performance />} />
            <Route path="/journal" element={<Journal />} />
            <Route path="/market" element={<MarketAnalysis />} />
            <Route path="/risk" element={<RiskManagement />} />
            <Route path="/backtests" element={<Backtests />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </div>
  );
}

export default App;
