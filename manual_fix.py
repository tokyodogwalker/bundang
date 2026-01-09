import psycopg2

# 1. DB 연결 설정 (포트 5433)
pg_config = {
    'host': 'localhost',
    'user': 'postgres',
    'password': 'root',
    'dbname': 'bundang_apt',
    'port': 5433
}

def fix_kumho_hanyang():
    conn = psycopg2.connect(**pg_config)
    cursor = conn.cursor()
    
    print("🛠️ 마지막 작업: 금호3차 + 한양5단지 통합 수정 시작...")

    # 타겟: 수내양지마을금호3차 (코드: A46392001)
    target_code = 'A46392001'
    
    # 변경할 내용:
    # 이름 -> 양지3,5단지금호한양아파트
    # 좌표 -> 37.375206... (아까 주신 5단지 좌표)
    new_name = '양지3,5단지금호한양아파트'
    new_lat = 37.37409774585746
    new_lng = 127.11537283092484

    # 1. 업데이트 실행
    sql = """
        UPDATE apartments 
        SET name = %s, lat = %s, lng = %s 
        WHERE apt_code = %s
    """
    cursor.execute(sql, (new_name, new_lat, new_lng, target_code))
    
    if cursor.rowcount > 0:
        print(f"✅ 성공! 금호3차(A46392001)가 '{new_name}'로 변경되었습니다.")
        print(f"📍 좌표 적용 완료: {new_lat}, {new_lng}")
    else:
        print(f"⚠️ 실패: 코드 '{target_code}'를 찾을 수 없습니다.")

    # 2. 결과 확인
    conn.commit()
    conn.close()

if __name__ == "__main__":
    fix_kumho_hanyang()