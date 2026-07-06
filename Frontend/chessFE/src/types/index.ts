export type Color = 'white' | 'black';
export type GameStatus = 'waiting' | 'playing' | 'finished';

export interface Clocks {
  white: number;
  black: number;
}

export interface RoomState {
  roomId: string;
  status: GameStatus;
  timeControl: string;
  timeControlMs: number;
  players: {
    white: { connected: boolean } | null;
    black: { connected: boolean } | null;
  };
  fen: string;
  turn: Color;
  clocks: Clocks;
  moves: string[];
}

export interface GameStartedPayload {
  fen: string;
  turn: Color;
  clocks: Clocks;
  moves: string[];
}

export interface MoveMadePayload {
  san: string;
  from: string;
  to: string;
  promotion?: string;
  fen: string;
  turn: Color;
  clocks: Clocks;
  moveNumber: number;
}

export interface GameOverPayload {
  result: string;
  reason: string;
}

export interface AiAnalysisData {
  white_elo: number;
  black_elo: number;
  eco: {
    code: string;
    name: string;
  };
  stats: {
    white_avg_cpl: number;
    black_avg_cpl: number;
    white_blunders: number;
    black_blunders: number;
    total_moves: number;
  };
  explanation: string;
  cpl_sequence?: number[];
  blunder_flags?: number[];
  critical_blunders?: Array<{
    move_index: number;
    move_san: string;
    side: string;
    reason?: string;
  }>;
}

export interface AnalysisResultPayload {
  success: boolean;
  data?: AiAnalysisData;
  basicResult?: string;
  error?: string;
}
