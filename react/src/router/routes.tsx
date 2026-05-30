import Home from "@/views/Home";
import AIChat from "@/views/AIChat";
import KnowledgeBase from "@/views/KnowledgeBase";
import Weather from "@/views/Weather";
import Profile from "@/views/Profile";
import IdentificationResult from "@/views/IdentificationResult";
import ErrorPage from "@/views/ErrorPage";
import EmptyState from "@/views/EmptyState";

export const routes = [
  { path: "/", component: Home, guid: "home" },
  { path: "/home", component: Home, guid: "home" },
  { path: "/ai-chat", component: AIChat, guid: "ai-chat" },
  { path: "/knowledge", component: KnowledgeBase, guid: "knowledge" },
  { path: "/weather", component: Weather, guid: "weather" },
  { path: "/profile", component: Profile, guid: "profile" },
  { path: "/identification-result", component: IdentificationResult, guid: "identification" },
  { path: "/error", component: ErrorPage, guid: "error" },
  { path: "/history", component: () => <EmptyState type="history" />, guid: "history" },
  { path: "/chat-empty", component: () => <EmptyState type="chat" />, guid: "chat-empty" },
];

export const guidPathMap = new Map(routes.map((item) => [item.guid, item.path]));
export const pathGuidMap = new Map(routes.map((item) => [item.path, item.guid]));
export const getPathByGuid = (guid: string) => guidPathMap.get(guid) || "";
export const getGuidByPath = (path: string) => pathGuidMap.get(path) || "";
