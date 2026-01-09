from flask import Flask, render_template, jsonify

import psycopg2

from psycopg2.extras import RealDictCursor

import os

###### 잘 안되면 app.py_v2로 해

app = Flask(__name__)



def calculate_bomb_risk(apt):

    """

    [관리비 폭탄 위험도 계산기 v3.0 - 선도지구 예외 적용]

    """

    risk_score = 0

    reasons = []



    # 0. 데이터 가져오기

    age = apt.get('age', 0)

    is_leading = apt.get('is_leading_zone', False)  # 선도지구 여부

    is_special = apt.get('is_special_act', False)   # 특별법 여부 (선도지구 신청 등)

   

    # 관리비 파싱

    try:

        monthly_fee_str = str(apt.get('monthly_fee', '0')).replace(',', '').replace('원', '').strip()

        monthly_fee = int(monthly_fee_str) if monthly_fee_str.isdigit() else 0

    except:

        monthly_fee = 0



    # 수선 이력 확인

    repair_elevator = apt.get('repair_elevator', '-')

    repair_plumbing = apt.get('repair_plumbing', '-')

    repair_paint = apt.get('repair_paint', '-')

   

    no_repairs = 0

    if repair_elevator in ['-', ''] : no_repairs += 1

    if repair_plumbing in ['-', ''] : no_repairs += 1

    if repair_paint in ['-', ''] : no_repairs += 1



    # =========================================================

    # ★ [핵심] 선도지구 프리패스 (면죄부 발급)

    # =========================================================

    if is_leading:

        return "선도지구", "blue", ["재건축 확정으로 유지보수 최소화"]

   

    # (선택사항) 특별법 대상인데 아직 선도지구는 아닌 경우 -> 참작해줌

    if is_special and monthly_fee < 500:

        # 점수는 매기되, 빨간불까진 안 가게 조절하거나 별도 표시

        reasons.append("특별법 추진 중(유지보수 축소 예상)")

        # 여기서는 일단 폭탄 계산은 하되, 점수를 좀 깎아줄 수도 있음

        # 하지만 유지보수가 안 되면 불편한 건 사실이니 점수는 그대로 둡니다.



    # =========================================================

    # 1. [매운맛 심사] 여기서부터는 일반 단지 기준

    # =========================================================

   

    # (1) 연식 가중치

    if age >= 30:

        risk_score += 30

        reasons.append("30년차 이상 노후")

    elif age >= 20:

        risk_score += 15



    # (2) 돈 안 걷는 구두쇠 단지 (폭탄 제조 중)

    if age >= 20:

        if monthly_fee < 400: # 400원 미만은 진짜 심각

            risk_score += 50

            reasons.append(f"충당금 적립 극소({monthly_fee}원)")

        elif monthly_fee < 800:

            risk_score += 30

            reasons.append("충당금 적립 부족")

   

    # (3) 수선 방치 (몸테크 강요)

    if age >= 15 and no_repairs >= 2:

        risk_score += 20

        reasons.append("주요시설 수선 미비")



    # =========================================================

    # [최종 판정]

    # =========================================================

    if risk_score >= 60:

        return "폭탄주의", "red", reasons

    elif risk_score >= 30:

        return "관리필요", "orange", reasons

    else:

        return "양호", "green", reasons



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
            # 1. 좌표 및 기본 데이터 정리
            try:
                lat = float(row['lat']) if row['lat'] else 0.0
                lng = float(row['lng']) if row['lng'] else 0.0
            except:
                lat, lng = 0.0, 0.0

            build_year = row['build_date'].year if row.get('build_date') else 2025
            age = 2025 - build_year

            # 돈 관련 계산
            fee_total = row.get('long_term_charge') or 0
            area = row.get('area') or 1
            fee_per_m2 = round(fee_total / area) if fee_total > 0 and area > 0 else 0
            balance_val = row.get('long_term_balance') or 0
            
            # 수선 상태 정리
            pipe = row.get('pipe_status') or "-"
            elev = row.get('elev_status') or "-"
            p_stat = row.get('paint_status')
            w_stat = row.get('waterproof_status')
            
            valid_stats = []
            if p_stat and p_stat != "-": valid_stats.append(p_stat)
            if w_stat and w_stat != "-": valid_stats.append(w_stat)
            paint_water = ", ".join(valid_stats) if valid_stats else "-"

            # =========================================================
            # ★ [핵심] 여기서 아까 만든 '매운맛 판독기' 함수를 호출합니다!
            # =========================================================
            
            # 1. 판독기에 넣어줄 데이터 포장
            apt_data_for_calc = {
                'age': age,
                'monthly_fee': fee_per_m2,  # ㎡당 부과액
                'repair_elevator': elev,
                'repair_plumbing': pipe,
                'repair_paint': paint_water,
                'is_leading_zone': row.get('is_leading_zone'), # 선도지구 여부
                'is_special_act': row.get('is_special_act')    # 특별법 여부
            }

            # 2. 함수 실행! (결과: 등급, 색깔, 이유)
            status_text, color_code, risk_reasons = calculate_bomb_risk(apt_data_for_calc)
            
            # 3. 이유가 없으면 기본 멘트
            if not risk_reasons:
                if status_text == "양호": risk_reasons = ["관리 상태 무난함"]
                else: risk_reasons = ["특이사항 없음"]

            # 4. 결과 리스트에 담기
            results.append({
                "name": row['name'],
                "lat": lat, 
                "lng": lng,
                
                # ▼ 화면에 보여질 핵심 데이터
                "status": status_text,            # 폭탄주의 / 관리필요 / 양호 / 선도지구
                "color": color_code,              # red / orange / green / blue
                "desc": ", ".join(risk_reasons),  # 위험 이유 (콤마로 연결)
                
                "age": age,
                "balance": format_balance(balance_val),
                "fee": f"{fee_per_m2}원",
                "is_leading": row.get('is_leading_zone'),
                "history": { "pipe": pipe, "elev": elev, "paint_water": paint_water }
            })

        return jsonify(results)



    except Exception as e:

        print(f"에러: {e}")

        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":

    app.run(debug=True, port=5000)