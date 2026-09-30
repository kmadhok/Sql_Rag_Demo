import { useState } from "react";
import TopBar from "./workspace/TopBar.jsx";
import AskWorkspace from "./workspace/AskWorkspace.jsx";
import { useAsk } from "./workspace/useAsk.js";
import Board from "./board/Board.jsx";
import { useBoard } from "./board/useBoard.js";

function App() {
  const [view, setView] = useState("ask");
  const ask = useAsk();
  const board = useBoard();

  return (
    <div className="flex h-dvh flex-col bg-canvas text-zinc-200">
      <TopBar view={view} onViewChange={setView} pinCount={board.pins.length} />
      {view === "ask" ? (
        <AskWorkspace ask={ask} board={board} />
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto">
          <Board board={board} onGoToAsk={() => setView("ask")} />
        </div>
      )}
    </div>
  );
}

export default App;
