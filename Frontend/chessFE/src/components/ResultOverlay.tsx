import React from 'react';
import type { AnalysisResultPayload, Color } from '../types';
import { Button } from './Button';
import {
  Trophy,
  Frown,
  LineChart,
  AlertTriangle,
  MessageSquare,
  RotateCcw,
  ChevronDown,
  User,
} from 'lucide-react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  AreaChart,
  Area,
} from 'recharts';
import ReactMarkdown from 'react-markdown';
import { cn } from '../utils/cn';

interface ResultOverlayProps {
  result: { result: string; reason: string };
  analysis: AnalysisResultPayload | null;
  myColor: Color;
  onNewGame: () => void;
}

export const ResultOverlay: React.FC<ResultOverlayProps> = ({
  result,
  analysis,
  myColor,
  onNewGame,
}) => {
  const isWinner =
    (result.result === '1-0' && myColor === 'white') ||
    (result.result === '0-1' && myColor === 'black');

  const isDraw = result.result === '1/2-1/2';

  const chartData = analysis?.data?.cpl_sequence?.map((cpl, i) => ({
    move: i + 1,
    cpl,
    isBlunder: analysis.data?.blunder_flags?.[i] === 1,
  }));

  return (
    <div className="fixed inset-0 z-50 bg-bg/95 overflow-y-auto pt-10 pb-20 px-4">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="text-center space-y-4">
          <div className="inline-flex items-center justify-center p-6 bg-surface rounded-full border-4 border-accent/20 shadow-accent/10 shadow-2xl">
            {isDraw ? (
              <LineChart className="w-16 h-16 text-warning" />
            ) : isWinner ? (
              <Trophy className="w-16 h-16 text-accent animate-bounce" />
            ) : (
              <Frown className="w-16 h-16 text-danger" />
            )}
          </div>
          <h1 className="text-4xl font-black italic">
            {isDraw ? 'HÒA CỜ' : isWinner ? 'BẠN ĐÃ THẮNG!' : 'BẠN ĐÃ THUA'}
          </h1>
          <p className="text-muted uppercase tracking-widest text-sm">
            Lý do: {result.reason} • Kết quả: {result.result}
          </p>
          <Button size="lg" onClick={onNewGame} className="mt-4">
            <RotateCcw className="w-5 h-5 mr-2" />
            Chơi ván mới
          </Button>
        </div>

        {!analysis && (
          <div className="bg-surface p-12 rounded-2xl border border-border text-center">
            <div className="animate-spin w-8 h-8 border-4 border-accent border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-muted">Đang chờ AI phân tích ván đấu...</p>
          </div>
        )}

        {analysis && !analysis.success && (
          <div className="bg-danger/10 border border-danger/20 p-6 rounded-2xl text-center">
            <AlertTriangle className="w-8 h-8 text-danger mx-auto mb-2" />
            <p className="text-danger font-bold">AI Service không khả dụng</p>
            <p className="text-xs text-danger/70 mt-1">{analysis.error || 'Vui lòng thử lại sau'}</p>
          </div>
        )}

        {analysis?.success && analysis.data && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-3 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="bg-surface p-6 rounded-2xl border border-border relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-5">
                  <User size={80} />
                </div>
                <p className="text-muted text-sm font-bold uppercase mb-1">Dự đoán ELO Trắng</p>
                <h3 className="text-5xl font-black text-accent">{analysis.data.white_elo}</h3>
                <p className="text-xs text-muted mt-2">Avg CPL: {analysis.data.stats.white_avg_cpl.toFixed(1)}</p>
              </div>
              <div className="bg-surface p-6 rounded-2xl border border-border relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-5">
                  <User size={80} />
                </div>
                <p className="text-muted text-sm font-bold uppercase mb-1">Dự đoán ELO Đen</p>
                <h3 className="text-5xl font-black text-accent">{analysis.data.black_elo}</h3>
                <p className="text-xs text-muted mt-2">Avg CPL: {analysis.data.stats.black_avg_cpl.toFixed(1)}</p>
              </div>
            </div>

            <div className="md:col-span-2 space-y-6">
              {chartData && (
                <div className="bg-surface p-6 rounded-2xl border border-border">
                  <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
                    <LineChart size={20} className="text-accent" />
                    Biểu đồ ưu thế (CPL)
                  </h3>
                  <div className="h-64 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={chartData}>
                        <defs>
                          <linearGradient id="colorCpl" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#E8B959" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#E8B959" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#262B38" vertical={false} />
                        <XAxis dataKey="move" stroke="#9AA3B2" fontSize={12} tickLine={false} />
                        <YAxis stroke="#9AA3B2" fontSize={12} tickLine={false} axisLine={false} />
                        <Tooltip
                          contentStyle={{ backgroundColor: '#1C212D', border: '1px solid #262B38', borderRadius: '8px' }}
                          itemStyle={{ color: '#E8B959' }}
                        />
                        <ReferenceLine y={0} stroke="#9AA3B2" strokeWidth={1} />
                        <Area
                          type="monotone"
                          dataKey="cpl"
                          stroke="#E8B959"
                          fillOpacity={1}
                          fill="url(#colorCpl)"
                          strokeWidth={3}
                          dot={(props: any) => {
                            if (props.payload.isBlunder) {
                              return <circle cx={props.cx} cy={props.cy} r={4} fill="#E5484D" stroke="none" />;
                            }
                            return null as any;
                          }}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                  <p className="text-[10px] text-muted mt-4 italic">
                    * Giá trị CPL dương thể hiện ưu thế cho Trắng, âm thể hiện ưu thế cho Đen. Dấu đỏ là Blunder.
                  </p>
                </div>
              )}

              {analysis.data.critical_blunders && analysis.data.critical_blunders.length > 0 && (
                <div className="bg-surface rounded-2xl border border-border overflow-hidden">
                  <div className="p-4 border-b border-border bg-bg/20">
                    <h3 className="text-lg font-bold flex items-center gap-2">
                      <AlertTriangle size={20} className="text-danger" />
                      Các sai lầm nghiêm trọng
                    </h3>
                  </div>
                  <div className="divide-y divide-border">
                    {analysis.data.critical_blunders.map((blunder, i) => (
                      <div key={i} className="p-4 flex items-center justify-between hover:bg-elevated transition-colors">
                        <div className="flex items-center gap-4">
                          <div
                            className={cn(
                              'w-10 h-10 rounded-lg flex items-center justify-center font-bold',
                              blunder.side === 'white' ? 'bg-text text-bg' : 'bg-bg text-text border border-border'
                            )}
                          >
                            {blunder.move_san}
                          </div>
                          <div>
                            <p className="text-sm font-bold">Nước thứ {Math.floor(blunder.move_index / 2) + 1}</p>
                            <p className="text-xs text-muted">{blunder.reason || 'Sai lầm làm thay đổi cục diện ván đấu'}</p>
                          </div>
                        </div>
                        <ChevronDown size={16} className="text-muted" />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="md:col-span-1 space-y-6">
              <div className="bg-surface p-6 rounded-2xl border border-border h-full flex flex-col">
                <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                  <MessageSquare size={20} className="text-accent" />
                  Nhận xét của HLV
                </h3>
                <div className="prose prose-sm max-w-none flex-1">
                  <ReactMarkdown>{analysis.data.explanation}</ReactMarkdown>
                </div>
                <div className="mt-6 pt-6 border-t border-border flex items-center justify-between text-xs text-muted">
                  <span>
                    Khai cuộc: <strong className="text-accent">{analysis.data.eco.name}</strong>
                  </span>
                  <span className="font-mono">{analysis.data.eco.code}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
