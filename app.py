from flask import Flask, render_template, jsonify
import pymysql

app = Flask(__name__)

# --- [단위 변환] ---
def format_balance(val_won):
    if not val_won or val_won <= 0: return "정보 없음"
    uk = int(val_won // 100000000)
    cheon = int((val_won % 100000000) // 10000000)
    res = ""
    if uk > 0: res += f"{uk}억 "
    if cheon > 0: res += f"{cheon}천만원"
    return res.strip() if res else "1천만원 미만"

def get_db_connection():
    return pymysql.connect(
        host='localhost', user='root', password='root',
        db='bundang_apt', charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/data')
def get_apt_data():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = """
        SELECT a.*, f.long_term_balance, f.long_term_charge,
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
            age = 2025 - row['build_date'].year if row['build_date'] else 0
            area = row.get('area') or 1
            fee_total = row.get('long_term_charge') or 0
            fee_per_m2 = round(fee_total / area) if fee_total > 0 else 0
            balance_val = row.get('long_term_balance') or 0
            
            is_leading = row.get('is_leading_zone')
            is_special = row.get('is_special_act')
            zone_name = row.get('zone_name') or "분당신도시"
            rem_stat = row.get('remodeling_status')
            
            p_raw = str(row.get('paint_status') or "-")
            w_raw = str(row.get('waterproof_status') or "-")
            pw_list = []
            if p_raw != "-": pw_list.append(p_raw.replace(")", "도장)"))
            if w_raw != "-": pw_list.append(w_raw.replace(")", "방수)"))
            combined_pw = ", ".join(pw_list) if pw_list else "-"

            history_all = [str(row.get('pipe_status')), str(row.get('elev_status')), p_raw, w_raw]
            has_recent_work = any("202" in s for s in history_all)

            # --- [누님의 최종 필터링 로직] ---
            risk = "mid"
            desc = ""

            # 1순위: 신축 (0~5년)
            if age <= 5:
                risk = "safe"
                desc = f"✨ {age}년차 갓 지은 신축! 노후도 걱정 제로, 분당의 자부심입니다."
            
            # 2순위: 리모델링 (여기야 누님! 🚧)
            elif rem_stat:
                risk = "remodel"
                # 누님이 요청한 'Old 데이터 안내' 멘트로 교체했어!
                desc = f"🚧 현재 {rem_stat}! 기존 아파트 정보는 리모델링 전 데이터이며, 새 아파트로 탈바꿈 중입니다."
            
            # 3순위: 선도지구 (🏆)
            elif is_leading:
                risk = "leading"
                desc = f"🏆 1기 신도시 선도지구 확정! {age}년차지만 재건축 시계가 가장 빨리 돌아갑니다."
            
            # 4순위: 보통 (6~14년)
            elif 6 <= age <= 14:
                risk = "normal"
                desc = f"🙂 {age}년차 보통 단지. 아직은 실거주 만족도가 높고 무난한 시기예요."
            
            # 5순위: 노후 폭탄 (30년↑ + 노공사 + 노머니)
            elif age >= 30 and not has_recent_work and balance_val < 500000000:
                risk = "high"
                desc = f"😡 폭탄 단지 주의! {age}년 동안 방치됐고 돈도 부족.. 수리비 폭탄 터집니다!"
            
            # 6순위: 관리 잘된 구축
            elif has_recent_work:
                risk = "low"
                desc = "🛡️ 관리의 승리! 연차는 높지만 주요 공사를 싹 끝내서 재건축까지 든든합니다."
            
            # 7순위: 나머지 계륵
            else:
                risk = "mid"
                desc = f"🤔 {age}년차 계륵 단지. 재건축도 멀고 관리도 방치된 수준.. 냉정한 판단이 필요합니다."

            results.append({
                "name": row['name'], "lat": row['lat'], "lng": row['lng'],
                "fee": f"{fee_per_m2}원",
                "balance": format_balance(balance_val),
                "age": age,
                "risk": risk,
                "desc": desc,
                "is_leading": is_leading,
                "is_special": is_special,
                "zone_name": zone_name,
                "remodeling_status": rem_stat,
                "history": {
                    "pipe": row.get('pipe_status') or "-",
                    "elev": row.get('elev_status') or "-",
                    "paint_water": combined_pw
                }
            })
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)