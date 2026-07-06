import React, { useState } from 'react';
import { Button } from './Button';
import { Trophy, Play, Plus, LogIn } from 'lucide-react';
import { cn } from '../utils/cn';

interface LobbyProps {
  onCreateRoom: (minutes: number) => void;
  onJoinRoom: (roomId: string) => void;
  loading: boolean;
  error?: string | null;
}

export const Lobby: React.FC<LobbyProps> = ({ onCreateRoom, onJoinRoom, loading, error }) => {
  const [timeControl, setTimeControl] = useState(5);
  const [roomCode, setRoomCode] = useState('');

  const timeOptions = [3, 5, 10, 15];

  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] w-full max-w-md mx-auto p-6">
      <div className="mb-12 text-center">
        <div className="inline-flex items-center justify-center p-4 bg-surface rounded-2xl mb-4 border border-border">
          <Trophy className="w-12 h-12 text-accent" />
        </div>
        <h1 className="text-5xl font-black text-text tracking-tighter mb-2 italic">WHESS</h1>
        <p className="text-muted italic">Multi-Agent AI Chess Analysis</p>
      </div>

      <div className="w-full space-y-8">
        {/* Create Room Section */}
        <div className="bg-surface p-6 rounded-xl border border-border shadow-2xl">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Plus className="w-5 h-5 text-accent" />
            Tạo phòng mới
          </h2>
          <div className="grid grid-cols-4 gap-2 mb-4">
            {timeOptions.map((min) => (
              <button
                key={min}
                onClick={() => setTimeControl(min)}
                className={cn(
                  "py-2 rounded-md border transition-all font-medium",
                  timeControl === min 
                    ? "bg-accent/10 border-accent text-accent" 
                    : "border-border text-muted hover:border-muted"
                )}
              >
                {min}m
              </button>
            ))}
          </div>
          <Button 
            className="w-full" 
            onClick={() => onCreateRoom(timeControl)}
            loading={loading}
          >
            <Play className="w-4 h-4 mr-2 fill-current" />
            Bắt đầu Game
          </Button>
        </div>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-border"></span>
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-bg px-2 text-muted">Hoặc</span>
          </div>
        </div>

        {/* Join Room Section */}
        <div className="bg-surface p-6 rounded-xl border border-border">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <LogIn className="w-5 h-5 text-accent" />
            Vào phòng bằng mã
          </h2>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Mã phòng (VD: ABCXYZ)"
              value={roomCode}
              onChange={(e) => setRoomCode(e.target.value.toUpperCase())}
              className="flex-1 bg-bg border border-border rounded-md px-4 py-2 outline-none focus:border-accent text-text"
              maxLength={6}
            />
            <Button 
              variant="secondary" 
              onClick={() => onJoinRoom(roomCode)}
              disabled={!roomCode || roomCode.length < 3}
              loading={loading}
            >
              Vào
            </Button>
          </div>
        </div>

        {error && (
          <div className="bg-danger/10 border border-danger/20 text-danger p-3 rounded-md text-sm text-center">
            {error}
          </div>
        )}
      </div>
    </div>
  );
};
