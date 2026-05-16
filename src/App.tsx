import { Routes, Route } from "react-router";
import Layout from "@/components/Layout";
import Chat from "@/pages/Chat";
import Dashboard from "@/pages/Dashboard";
import KnowledgeGraph from "@/pages/KnowledgeGraph";
import Curriculum from "@/pages/Curriculum";
import Settings from "@/pages/Settings";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Chat />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/knowledge-graph" element={<KnowledgeGraph />} />
        <Route path="/curriculum" element={<Curriculum />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  );
}
