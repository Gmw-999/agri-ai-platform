import { Component, PropsWithChildren } from 'react';
import './app.css';

interface PendingImage {
  base64: string;
  tempPath: string;
}

class App extends Component<PropsWithChildren> {
  globalData: { pendingImage: PendingImage | null } = {
    pendingImage: null,
  };

  componentDidShow() {}
  componentDidHide() {}

  render() {
    return this.props.children;
  }
}

export default App;
