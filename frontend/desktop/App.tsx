import { Link, Route, Routes } from "react-router-dom";
import { Home } from "@/components/Home";
import Analysis from "@/pages/AnalysisPage";
import Parties from "@/pages/PartiesPage";
import Protocol from "@/pages/ProtocolPage";
import Export from "@/pages/ExportPage";
import { RememberDocument, ResumeDocument } from "./session";

export function App() {
  return <>
    <RememberDocument />
    <a className="skip-link" href="#main-content">К содержимому</a>
    <Routes>
      <Route path="/" element={<Home resumeDocument={<ResumeDocument />} />} />
      <Route path="/documents/:id/analysis" element={<Analysis />} />
      <Route path="/documents/:id/parties" element={<Parties />} />
      <Route path="/documents/:id/protocol" element={<Protocol />} />
      <Route path="/documents/:id/export" element={<Export />} />
      <Route path="*" element={<main className="mx-auto max-w-6xl space-y-4 p-6"><h1>Этот раздел недоступен</h1><Link to="/">Открыть документ</Link></main>} />
    </Routes>
  </>;
}
