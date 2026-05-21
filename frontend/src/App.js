import React from "react";
import "./App.css";
import ChatWindow from "./components/ChatWindow";

function App() {
  return (
    <div className="App">
      <header className="header">
        <div className="header-inner">
          <img src="/partselect-logo.png" alt="PartSelect" height="36" />
        </div>
      </header>
      <ChatWindow />
    </div>
  );
}

export default App;
