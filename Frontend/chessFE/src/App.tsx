import { useState, useEffect, useCallback } from 'react';
import { socketService } from './services/socket';
import { Lobby } from './components/Lobby';
import { ChessRoom } from './components/ChessRoom';
import { ResultOverlay } from './components/ResultOverlay';
import type {
  RoomState,
  Color,
  GameStartedPayload,
  MoveMadePayload,
  GameOverPayload,
  AnalysisResultPayload,
} from './types';

const createInitialRoomState = (roomId: string): RoomState => ({
  roomId,
  status: 'waiting',
  timeControl: '',
  timeControlMs: 0,
  players: {
    white: { connected: true },
    black: null,
  },
  fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
  turn: 'white',
  clocks: { white: 0, black: 0 },
  moves: [],
});

function App() {
  const [screen, setScreen] = useState<'lobby' | 'room'>('lobby');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [myColor, setMyColor] = useState<Color>('white');
  const [roomState, setRoomState] = useState<RoomState | null>(null);
  const [gameOver, setGameOver] = useState<GameOverPayload | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResultPayload | null>(null);
  const [moveError, setMoveError] = useState<string | null>(null);

  useEffect(() => {
    const socket = socketService.connect();

    socket.on('room_created', ({ roomId, color }) => {
      setMyColor(color);
      setRoomState(createInitialRoomState(roomId));
      setScreen('room');
      setLoading(false);
      setError(null);
      setMoveError(null);
    });

    socket.on('room_joined', ({ roomId, color, state }) => {
      setMyColor(color);
      setRoomState(
        state
          ? ({ roomId, ...state } as RoomState)
          : createInitialRoomState(roomId ?? '')
      );
      setScreen('room');
      setLoading(false);
      setError(null);
      setMoveError(null);
    });

    socket.on('room_error', ({ message }) => {
      setError(message);
      setLoading(false);
      setMoveError(null);
    });

    socket.on('opponent_joined', () => {
      setError(null);
    });

    socket.on('connect', () => {
      setError(null);
    });

    socket.on('connect_error', (err) => {
      setError('Không thể kết nối server. Vui lòng kiểm tra backend.');
      setLoading(false);
      console.error('Socket connect error:', err);
    });

    socket.on('connect_timeout', () => {
      setError('Kết nối Socket.IO timeout.');
      setLoading(false);
    });

    socket.on('game_started', (payload: GameStartedPayload) => {
      setRoomState((prev) =>
        prev
          ? {
              ...prev,
              fen: payload.fen,
              turn: payload.turn,
              clocks: payload.clocks,
              moves: payload.moves,
              status: 'playing',
            }
          : createInitialRoomState('')
      );
      setScreen('room');
      setMoveError(null);
    });

    socket.on('move_made', (payload: MoveMadePayload) => {
      setRoomState((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          fen: payload.fen,
          turn: payload.turn,
          clocks: payload.clocks,
          moves: [...prev.moves, payload.san],
          status: 'playing',
        };
      });
      setMoveError(null);
    });

    socket.on('move_rejected', ({ reason }: { reason?: string }) => {
      setMoveError(reason ?? 'Nước đi không hợp lệ.');
    });

    socket.on('clock_update', ({ clocks, turn }: { clocks: RoomState['clocks']; turn: Color }) => {
      setRoomState((prev) => {
        if (!prev) return null;
        return { ...prev, clocks, turn };
      });
    });

    socket.on('game_over', (payload: GameOverPayload) => {
      setGameOver(payload);
      setRoomState((prev) => {
        if (!prev) return null;
        return { ...prev, status: 'finished' };
      });
      setAnalysis(null);
      setMoveError(null);
    });

    socket.on('analysis_result', (payload: AnalysisResultPayload) => {
      setAnalysis(payload);
    });

    socket.on('disconnect', () => {
      setScreen('lobby');
      setRoomState(null);
      setGameOver(null);
      setAnalysis(null);
      setMoveError(null);
    });

    return () => {
      socketService.disconnect();
    };
  }, []);

  const handleCreateRoom = useCallback((minutes: number) => {
    setLoading(true);
    setError(null);
    setMoveError(null);
    socketService.emit('create_room', { timeControlMinutes: minutes });
  }, []);

  const handleJoinRoom = useCallback((roomId: string) => {
    setLoading(true);
    setError(null);
    setMoveError(null);
    socketService.emit('join_room', { roomId });
  }, []);

  const handleMove = useCallback((from: string, to: string, promotion?: string) => {
    if (!roomState) return;
    socketService.emit('make_move', {
      roomId: roomState.roomId,
      from,
      to,
      promotion,
    });
  }, [roomState]);

  const handleResign = useCallback(() => {
    if (!roomState) return;
    socketService.emit('resign', { roomId: roomState.roomId });
  }, [roomState]);

  const handleLeave = useCallback(() => {
    if (!roomState) return;
    socketService.emit('leave_room', { roomId: roomState.roomId });
    setScreen('lobby');
    setRoomState(null);
    setGameOver(null);
    setAnalysis(null);
    setMoveError(null);
  }, [roomState]);

  const handleNewGame = useCallback(() => {
    setScreen('lobby');
    setRoomState(null);
    setGameOver(null);
    setAnalysis(null);
    setMoveError(null);
  }, []);

  return (
    <div className="min-h-screen bg-bg text-text">
      {screen === 'lobby' ? (
        <Lobby
          onCreateRoom={handleCreateRoom}
          onJoinRoom={handleJoinRoom}
          loading={loading}
          error={error}
        />
      ) : roomState ? (
        <ChessRoom
          roomState={roomState}
          myColor={myColor}
          onMove={handleMove}
          onResign={handleResign}
          onLeave={handleLeave}
          moveError={moveError}
        />
      ) : null}

      {gameOver && (
        <ResultOverlay
          result={gameOver}
          analysis={analysis}
          myColor={myColor}
          onNewGame={handleNewGame}
        />
      )}
    </div>
  );
}

export default App;
