import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes, Link } from "react-router-dom";
import Home from "../app/page";
import Analysis from "../app/documents/[id]/analysis/page";
import Parties from "../app/documents/[id]/parties/page";
import Protocol from "../app/documents/[id]/protocol/page";
import Export from "../app/documents/[id]/export/page";
import { RememberDocument, ResumeDocument } from "./session";
import "../app/globals.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <RememberDocument />
      <a className="skip-link" href="#main-content">К содержимому</a>
      <Routes>
        <Route path="/" element={<><ResumeDocument /><Home /></>} />
        <Route path="/documents/:id/analysis" element={<Analysis />} />
        <Route path="/documents/:id/parties" element={<Parties />} />
        <Route path="/documents/:id/protocol" element={<Protocol />} />
        <Route path="/documents/:id/export" element={<Export />} />
        <Route path="*" element={<main className="workspace"><h1>Страница не найдена</h1><Link to="/">Открыть документ</Link></main>} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
);
