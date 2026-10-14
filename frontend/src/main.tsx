import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import App from "./App";
import RunPage from "./pages/RunPage";
import "./index.css";
import "./App.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/runs/:runId" element={<RunPage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
