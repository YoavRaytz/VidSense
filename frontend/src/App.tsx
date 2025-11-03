import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import IngestPage from "./pages/IngestPage";
import VideosPage from "./pages/VideosPage";
import SearchPage from "./pages/SearchPage";
import CollectionsPage from "./pages/CollectionsPage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-nav">
        <div className="app-nav-inner">
          <NavLink to="/ingest" className={({isActive}) => "nav-link" + (isActive ? " active" : "")}>Ingest</NavLink>
          <NavLink to="/videos" className={({isActive}) => "nav-link" + (isActive ? " active" : "")}>Videos</NavLink>
          <NavLink to="/search" className={({isActive}) => "nav-link" + (isActive ? " active" : "")}>Search</NavLink>
          <NavLink to="/collections" className={({isActive}) => "nav-link" + (isActive ? " active" : "")}>Collections</NavLink>
        </div>
      </div>
      <div className="container">
        <Routes>
          <Route path="/ingest" element={<IngestPage/>} />
          <Route path="/videos" element={<VideosPage/>} />
          <Route path="/search" element={<SearchPage/>} />
          <Route path="/collections" element={<CollectionsPage/>} />
          <Route path="*" element={<IngestPage/>} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
