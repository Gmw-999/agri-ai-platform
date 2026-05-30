import { RouterView } from "./router";
import { AppProvider } from "./contexts/AppContext";

const App = () => {
  return (
    <AppProvider>
      <RouterView />
    </AppProvider>
  );
};

export default App;
