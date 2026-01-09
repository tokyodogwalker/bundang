from flask import Flask, render_template, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = Flask(__name__)

# [PostgreSQL 연결 설정]
def get_db_connection():
    return psycopg2.connect(
        host='localhost',
        user='postgres',       # 본인 postgres ID
        password='root',       # 본인 postgres 비밀번호
        dbname='bundang_apt',  # DB 이름
        port=5433,             # 5433
        cursor_factory=RealDictCursor 
    )

def format_balance(val_won):
    if not val_won or val_won <= 0: return "정보 없음"
    uk = int(val_won // 100000000)
    cheon = int((val_won % 100000000) // 10000000)
    res = ""
    if uk > 0: res += f"{uk}억 "
    if cheon > 0: res += f"{cheon}천만원"
    return res.strip()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/data')
def get_apt_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # PostgreSQL 쿼리
        sql = """
        SELECT a.*, 
               f.long_term_balance, f.long_term_charge,
               c.pipe_status, c.elev_status, c.paint_status, c.waterproof_status
        FROM apartments a
        LEFT JOIN monthly_fees f ON a.apt_code = f.apt_code
        LEFT JOIN construction_status c ON a.apt_code = c.apt_code
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for row in rows:
            # 1. 좌표 안전 처리
            try:
                lat = float(row['lat']) if row['lat'] else 0.0
                lng = float(row['lng']) if row['lng'] else 0.0
            except:
                lat, lng = 0.0, 0.0

            # 2. 날짜 및 나이 계산
            # Postgres는 날짜를 바로 객체로 줍니다. 없을 경우 대비해 2025년으로 처리
            build_year = row['build_date'].year if row.get('build_date') else 2025
            age = 2025 - build_year

            fee_total = row.get('long_term_charge') or 0
            area = row.get('area') or 1
            fee_per_m2 = round(fee_total / area) if fee_total > 0 and area > 0 else 0
            balance_val = row.get('long_term_balance') or 0
            
            # 3. 시설 상태 가공
            pipe = row.get('pipe_status') or "-"
            elev = row.get('elev_status') or "-"
            p_stat = row.get('paint_status')
            w_stat = row.get('waterproof_status')
            valid_stats = []
            if p_stat and p_stat != "-": valid_stats.append(p_stat)
            if w_stat and w_stat != "-": valid_stats.append(w_stat)
            paint_water = ", ".join(valid_stats) if valid_stats else "-"

            # 4. [핵심] 억울한 단지 구제 로직 (관리 우수 판독)
            full_history = str(pipe) + str(elev) + str(paint_water)
            good_signs = ["202", "2019", "전면", "전체", "교체", "개량"]
            is_managed_well = any(sign in full_history for sign in good_signs)

            # 5. 리스크 등급 매기기
            risk = "mid"
            desc = f"{age}년차 단지입니다."
            is_leading = row.get('is_leading_zone')
            rem_stat = row.get('remodeling_status')
            
            if age <= 5:
                risk = "safe"
                desc = "✨ 신축! 시설 상태 최상입니다."
            elif rem_stat:
                risk = "remodel"
                desc = f"🚧 {rem_stat} 진행 중! (미래 가치 주목)"
            elif is_leading:
                risk = "leading"
                desc = "🏆 선도지구 확정! 재건축 대장주."
            
            # 25년 이상 노후 단지 판별
            elif age >= 25: 
                if balance_val < 500000000: # 돈이 부족할 때
                    if is_managed_well:
                        risk = "low"
                        desc = "🛡️ 관리 우수! 최근 주요 시설 교체 완료. (장충금 잔액 감소는 공사비 지출 때문입니다)"
                    else:
                        risk = "high"
                        desc = "😡 수리비 폭탄 주의! 낡았는데 돈도 없고 수리 이력도 부족합니다."
                else:
                    risk = "normal"
                    desc = "🙂 연식은 됐지만 수리비(장충금)를 넉넉히 모아뒀습니다."
            else:
                risk = "normal"
                desc = "🙂 실거주하기 무난한 준신축급 단지입니다."
            
            results.append({
                "name": row['name'],
                "lat": lat, "lng": lng, "risk": risk, "age": age,
                "balance": format_balance(balance_val),
                "fee": f"{fee_per_m2}원",
                "desc": desc,
                "is_leading": is_leading,
                "is_special": row.get('is_special_act'),
                "zone_name": row.get('zone_name') or "",
                "history": { "pipe": pipe, "elev": elev, "paint_water": paint_water }
            })

        return jsonify(results)

    except Exception as e:
        print(f"에러: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)