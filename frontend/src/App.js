import React from "react";
import "./App.css";
import ChatWindow from "./components/ChatWindow";

function App() {
  return (
    <div className="App">
      <header className="header">
        <div className="header-inner">
          <img src="/partselect-logo.png" alt="PartSelect" height="36" width="auto" />
        </div>
      </header>
      <main>
        <ChatWindow />
      </main>
    </div>
  );
}

export default App;
