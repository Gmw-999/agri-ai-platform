import { Route, Routes, useLocation } from "react-router";
import { BrowserRouter as Router } from "react-router";
import { routes } from "./routes";

const RouterViewContent = () => {
  const location = useLocation();
  return (
    <Routes location={location} key={location.pathname}>
      {routes.map((route) => (
        <Route
          key={route.path}
          path={route.path}
          element={<route.component />}
        />
      ))}
    </Routes>
  );
};

export const RouterView = () => {
  return (
    <Router>
      <RouterViewContent />
    </Router>
  );
};
