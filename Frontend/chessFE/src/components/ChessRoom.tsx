import React, { useState, useEffect } from 'react';
import { Chessboard } from 'react-chessboard';
import { Chess, type Square } from 'chess.js';
import { Button } from './Button';
import { Clock, Flag, LogOut, User, Swords } from 'lucide-react';
import { cn, formatMs } from '../utils/cn';
import type { Color, RoomState } from '../types';

interface ChessRoomProps {
  roomState: RoomState;
  myColor: Color;
  onMove: (from: string, to: string, promotion?: string) => void;
  onResign: () => void;
  onLeave: () => void;
  moveError?: string | null;
}

export const ChessRoom: React.FC<ChessRoomProps> = ({
  roomState,
  myColor,
  onMove,
  onResign,
  onLeave,
  moveError,
}) => {
  const safeClocks = roomState.clocks ?? { white: 0, black: 0 };
  const safePlayers = roomState.players ?? { white: null, black: null };
  const displayClocks = roomState.clocks ?? safeClocks;
  const displayPlayers = roomState.players ?? safePlayers;

  const [game, setGame] = useState(() => new Chess(roomState.fen));
  const [localClocks, setLocalClocks] = useState(displayClocks);

  useEffect(() => {
    setGame(new Chess(roomState.fen));
  }, [roomState.fen]);

  useEffect(() => {
    setLocalClocks(displayClocks);
  }, [displayClocks]);

  useEffect(() => {
    if (roomState.status !== 'playing') return;

    const interval = window.setInterval(() => {
      setLocalClocks((prev) => ({
        ...prev,
        [roomState.turn]: Math.max(0, prev[roomState.turn] - 1000),
      }));
    }, 1000);

    return () => window.clearInterval(interval);
  }, [roomState.status, roomState.turn]);

  function onDrop({ sourceSquare, targetSquare }: { sourceSquare: Square; targetSquare: Square }) {
    if (roomState.status !== 'playing') return false;
    if (roomState.turn !== myColor) return false;

    const moveData: { from: string; to: string; promotion?: string } = {
      from: sourceSquare,
      to: targetSquare,
    };

    const previewGame = new Chess(game.fen());
    const piece = previewGame.get(sourceSquare);
    if (piece?.type === 'p' && (targetSquare[1] === '8' || targetSquare[1] === '1')) {
      moveData.promotion = 'q';
    }

    try {
      const move = previewGame.move(moveData);
      if (move) {
        onMove(moveData.from, moveData.to, moveData.promotion);
        return true;
      }
    } catch {
      return false;
    }
    return false;
  }

  const isMyTurn = roomState.turn === myColor && roomState.status === 'playing';
  const opponentColor = myColor === 'white' ? 'black' : 'white';

  if (!roomState.players || !roomState.clocks) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6 text-center text-text">
        <div className="max-w-lg rounded-3xl border border-border bg-surface p-8">
          <h2 className="text-2xl font-bold mb-4">Đang chờ dữ liệu phòng...</h2>
          <p className="text-sm text-muted mb-6">
            Có vẻ thông tin phòng chưa tải đầy đủ. Vui lòng quay lại Lobby và thử lại.
          </p>
          <Button onClick={onLeave}>Quay lại Lobby</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col lg:flex-row gap-8 items-start justify-center max-w-6xl mx-auto p-4 w-full">
      <div className="w-full lg:w-[600px] flex flex-col gap-4">
        <div
          className={cn(
            'flex items-center justify-between p-3 rounded-lg border',
            roomState.turn === opponentColor ? 'bg-surface border-accent/50' : 'bg-surface/50 border-border'
          )}
        >
          <div className="flex items-center gap-3">
            <div
              className={cn(
                'w-10 h-10 rounded-full flex items-center justify-center',
                opponentColor === 'white' ? 'bg-text text-bg' : 'bg-bg text-text border border-border'
              )}
            >
              <User size={20} />
            </div>
            <div>
              <p className="font-bold">{opponentColor === 'white' ? 'Trắng' : 'Đen'}</p>
              <p className="text-xs text-muted">{displayPlayers[opponentColor]?.connected ? 'Đã kết nối' : 'Đang chờ...'}</p>
            </div>
          </div>
          <div
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded font-mono text-2xl font-bold',
              roomState.turn === opponentColor ? 'text-accent bg-accent/10' : 'text-muted'
            )}
          >
            <Clock size={20} />
            {formatMs(localClocks[opponentColor] ?? 0)}
          </div>
        </div>

        <div className="aspect-square w-full shadow-2xl rounded-lg overflow-hidden border-4 border-surface">
          <Chessboard
            options={{
              position: roomState.fen,
              onPieceDrop: ({ sourceSquare, targetSquare }) => onDrop({ sourceSquare: sourceSquare as Square, targetSquare: targetSquare as Square }),
              boardOrientation: myColor,
              darkSquareStyle: { backgroundColor: '#3B4252' },
              lightSquareStyle: { backgroundColor: '#E8E4DA' },
              animationDurationInMs: 200,
            }}
          />
        </div>

        {moveError && (
          <div className="rounded-lg border border-danger/20 bg-danger/10 px-3 py-2 text-sm text-danger">
            {moveError}
          </div>
        )}

        <div
          className={cn(
            'flex items-center justify-between p-3 rounded-lg border',
            roomState.turn === myColor ? 'bg-surface border-accent/50' : 'bg-surface/50 border-border'
          )}
        >
          <div className="flex items-center gap-3">
            <div
              className={cn(
                'w-10 h-10 rounded-full flex items-center justify-center',
                myColor === 'white' ? 'bg-text text-bg' : 'bg-bg text-text border border-border'
              )}
            >
              <User size={20} />
            </div>
            <div>
              <p className="font-bold">{myColor === 'white' ? 'Trắng (Bạn)' : 'Đen (Bạn)'}</p>
              <p className="text-xs text-success">Đã kết nối</p>
            </div>
          </div>
          <div
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded font-mono text-2xl font-bold',
              roomState.turn === myColor ? 'text-accent bg-accent/10' : 'text-muted'
            )}
          >
            <Clock size={20} />
            {formatMs(localClocks[myColor] ?? 0)}
          </div>
        </div>
      </div>

      <div className="w-full lg:w-80 flex flex-col gap-4 self-stretch">
        <div className="bg-surface rounded-xl border border-border flex-1 flex flex-col overflow-hidden">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <h2 className="font-bold flex items-center gap-2">
              <Swords size={18} className="text-accent" />
              Lịch sử nước đi
            </h2>
            <span className="text-xs px-2 py-1 bg-bg rounded text-muted font-mono">
              ROOM: {roomState.roomId}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto p-2 grid grid-cols-2 gap-x-2 gap-y-1 content-start font-mono text-sm">
            {roomState.moves.map((move, i) => (
              <div
                key={`${move}-${i}`}
                className={cn('px-2 py-1 rounded flex gap-2', i % 2 === 0 ? 'bg-bg/50' : '')}
              >
                <span className="text-muted w-6">{Math.floor(i / 2) + 1}.</span>
                <span className="font-bold text-text">{move}</span>
              </div>
            ))}
            {roomState.moves.length === 0 && (
              <div className="col-span-2 text-center py-8 text-muted italic text-xs">
                Chưa có nước đi nào
              </div>
            )}
          </div>

          <div className="p-4 border-t border-border bg-bg/30 space-y-2">
            <div className="flex gap-2">
              <Button
                variant="danger"
                className="flex-1"
                size="sm"
                onClick={onResign}
                disabled={roomState.status !== 'playing'}
              >
                <Flag size={14} className="mr-1" />
                Xin thua
              </Button>
              <Button variant="secondary" className="flex-1" size="sm" onClick={onLeave}>
                <LogOut size={14} className="mr-1" />
                Rời phòng
              </Button>
            </div>
            {isMyTurn && (
              <div className="text-center py-2 bg-accent/10 text-accent rounded text-sm font-bold animate-pulse">
                Đến lượt của bạn
              </div>
            )}
            {!isMyTurn && roomState.status === 'playing' && (
              <div className="text-center py-2 text-muted text-sm">Đang chờ đối thủ...</div>
            )}
            {roomState.status === 'waiting' && (
              <div className="text-center py-2 text-warning text-sm font-medium">
                Đang chờ người chơi thứ 2...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
