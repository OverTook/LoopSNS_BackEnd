import csv
from config import BASE_DIR, kakaoapi
from PyKakao import Local

def _code2addr(code: str) -> dict:
    '''Params:
            code `str`:
                토지 코드 (2자리: 시도, 5자리: 시도 시군구, 8자리: 시도 시군구 읍면동, 19자리: 전체 주소)
            scale `int` (default=0):
                주소 단위 (0: 전체, 1: 시도, 2: 시군구, 3: 읍면동)
    '''
    with open(BASE_DIR + '/data/csv_data/pnu_code.csv') as data:
        csv_mapping = list(csv.DictReader(data))

    addr_dict = {
        'address': '',
        'sido': '',
        'sigungu': '',
        'eupmyeondong': ''
    }

    for d in csv_mapping:
        if d['code'] == code[0:10]:
            addr_dict['sido'] = d['sido']
            addr_dict['sigungu'] = d['sigungu']
            addr_dict['eupmyeondong'] = d['eupmyeondong']
            if code[10] == "1":
                m = ""
            else:
                m = "산"
            main_n = int(code[11:15])
            sub_n = int(code[15:19])
            n = f"{main_n}-{sub_n}" if sub_n != 0 else f"{main_n}"
            if d["donglee"] != "":
                addr_dict['address'] = f"{d['sido']} {d['sigungu']} {d['eupmyeondong']} {d['donglee']} {m}{n}"
            else:
                addr_dict['address'] = f"{d['sido']} {d['sigungu']} {d['eupmyeondong']} {m}{n}"
            
    return addr_dict

def get_data(lat: float, lng: float) -> dict:
    '''입력된 좌표의 PNU 코드 조회
        
    Params:
        lat `float`: 
            위도 좌표
        lng `float`: 
            경도 좌표
        scale `int` (default=0):
            주소 단위 (0: 전체, 1: 시도, 2: 시군구, 3: 읍면동)
    
    Returns:
        address `str`:
            토지 지번 주소
    '''
    # 로컬 API 인스턴스 생성
    try:
        local = Local(service_key=kakaoapi.KAKAO_KEY)
        request_address = local.geo_coord2address(lng, lat, dataframe=False)
        request_region = local.geo_coord2regioncode(lng, lat, dataframe=False)
        
        if request_region == None:
            return None, None
        i = 0 if request_region['documents'][0]['region_type'] == 'B' else 1
        pnu = request_region['documents'][i]['code']
        address = request_region['documents'][i]['address_name']

        if request_address['documents'][i]['address']['mountain_yn'] == 'N':
            mountain = '1'   # 산 X
        else:
            mountain = '2'   # 산 O

        # 본번과 부번의 포멧을 '0000'으로 맞춰줌
        main_no = request_address['documents'][0]['address']['main_address_no'].zfill(4)
        sub_no = request_address['documents'][0]['address']['sub_address_no'].zfill(4)
        pnu = str(pnu + mountain + main_no + sub_no)
        address = _code2addr(pnu)
    
        return address
    except:
        return {
            'sido': '',
            'sigungu': '',
            'eupmyeondong': ''
        }
