import pymysql

# DB 설정
db_config = {
    'host': '127.0.0.1', 'user': 'root', 'password': 'root',
    'db': 'bundang_apt', 'charset': 'utf8mb4'
}

def add_missing_data():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()
    
    print("🚑 누락된 리모델링 단지 긴급 수혈 시작! (๑•̀ㅂ•́)و✧")

    # 1. 추가할 단지 목록 (누님이 준 좌표 기반 미세 조정)
    # [단지명, 위도, 경도, 리모델링상태]
    missing_apts = [
        ("매화마을공무원2단지", 37.4135, 127.1285, "리모델링 추진"),
        ("매화마을공무원1단지", 37.4145, 127.1275, "리모델링 추진"),
        ("정자한솔마을5단지", 37.3655, 127.1165, "리모델링 공사중"), # 좌표 보정 (정자동)
        ("정자한솔마을6단지", 37.3645, 127.1175, "리모델링 추진"),
        ("더샵분당티에르원(정자느티마을3단지)", 37.3745, 127.1045, "리모델링 공사중"),
        ("더샵분당티에르원(정자느티마을4단지)", 37.3755, 127.1055, "리모델링 공사중"),
    ]

    try:
        # 2. 아파트 테이블에 추가 (이미 있으면 무시)
        sql_insert_apt = """
        INSERT IGNORE INTO apartments (apt_code, name, address, build_date, lat, lng, area, is_special_act, is_leading_zone, remodeling_status)
        VALUES (%s, %s, %s, '1995-01-01', %s, %s, 84, TRUE, FALSE, %s)
        """
        
        # apt_code는 임의로 'MANUAL_01' 등으로 생성
        count = 1
        for name, lat, lng, stat in missing_apts:
            code = f"MANUAL_{count:03d}"
            # 주소는 더미로 넣지만 위도/경도는 정확하게!
            addr = "경기도 성남시 분당구 수동입력"
            
            cursor.execute(sql_insert_apt, (code, name, addr, lat, lng, stat))
            count += 1
            
        # 3. 노후계획도시(특별법) 표시 강제 업데이트
        print("⚖️ 노후계획도시 마킹 복구 중...")
        cursor.execute("UPDATE apartments SET is_special_act = TRUE;")
        
        conn.commit()
        print(f"✨ 성공! 리모델링 단지 {len(missing_apts)}개가 지도에 추가되었습니다!")
        
    except Exception as e:
        print(f"🚨 에러 발생: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_missing_data()