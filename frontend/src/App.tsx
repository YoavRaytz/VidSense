import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import IngestPage from "./pages/IngestPage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-nav">
        <div className="app-nav-inner">
          <NavLink to="/ingest" className={({isActive}) => "nav-link" + (isActive ? " active" : "")}>Ingest</NavLink>
          <NavLink to="/videos" className={({isActive}) => "nav-link" + (isActive ? " active" : "")}>Videos</NavLink>
          <NavLink to="/search" className={({isActive}) => "nav-link" + (isActive ? " active" : "")}>Search</NavLink>
        </div>
      </div>
      <div className="container">
        <Routes>
          <Route path="/ingest" element={<IngestPage/>} />
          <Route path="/videos" element={<div className="card">Videos – coming next</div>} />
          <Route path="/search" element={<div className="card">Search – coming next</div>} />
          <Route path="*" element={<IngestPage/>} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
