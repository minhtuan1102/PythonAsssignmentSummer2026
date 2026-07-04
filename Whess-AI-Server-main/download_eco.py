import urllib.request
import json
import csv
import io
import os

def download_full_eco():
    print("Đang tải dữ liệu Bách khoa toàn thư Khai cuộc (ECO) từ Lichess...")
    
    # 5 file TSV chính thức từ Lichess (A, B, C, D, E)
    base_url = "https://raw.githubusercontent.com/lichess-org/chess-openings/master"
    files = ["a.tsv", "b.tsv", "c.tsv", "d.tsv", "e.tsv"]
    
    all_openings = []
    
    for fname in files:
        url = f"{base_url}/{fname}"
        print(f"  Đang tải {fname}...")
        try:
            req = urllib.request.urlopen(url)
            content = req.read().decode("utf-8")
            reader = csv.DictReader(io.StringIO(content), delimiter="\t")
            
            for row in reader:
                eco_code = row.get("eco", "").strip()
                name = row.get("name", "").strip()
                pgn = row.get("pgn", "").strip()
                
                if not eco_code or not pgn:
                    continue
                
                # Chuyển PGN "1. e4 e5 2. Nf3 Nc6" thành mảng SAN ["e4", "e5", "Nf3", "Nc6"]
                moves = []
                for token in pgn.split():
                    # Bỏ số thứ tự nước đi (1. 2. 3. ...)
                    if token[0].isdigit() and "." in token:
                        continue
                    moves.append(token)
                
                all_openings.append({
                    "code": eco_code,
                    "name": name,
                    "moves": moves
                })
                
        except Exception as e:
            print(f"  ❌ Lỗi khi tải {fname}: {e}")
    
    # Ghi đè file eco.json
    target_dir = os.path.join("src", "ai_engine", "services", "eco_data")
    os.makedirs(target_dir, exist_ok=True)
    target_file = os.path.join(target_dir, "eco.json")
    
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(all_openings, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Tải thành công {len(all_openings)} khai cuộc!")
    print(f"✅ Đã lưu vào: {target_file}")

if __name__ == "__main__":
    download_full_eco()
