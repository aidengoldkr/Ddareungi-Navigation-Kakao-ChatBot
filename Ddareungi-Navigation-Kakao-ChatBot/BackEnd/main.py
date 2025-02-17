import requests
from haversine import haversine
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from tempfile import mkdtemp
import json
import time

debuging_mode = True
able_bike = True

def handler(event, context):
    print(event)
    body = json.loads(event['body'])
    start = body['start']
    end = body['end']
    driver,action = create_driver()

    final_route = make_route(start,end,driver,action)
    print(final_route)
    if (type(final_route)) == list:
        listcard_list = make_listcard_list(final_route)
        return {
        'statusCode': 200,
        'body': json.dumps({'result': listcard_list})
        }
    else:
        return {
        'statusCode': 200,
        'body': json.dumps({'result': final_route})
        }


def create_driver():
    options = webdriver.ChromeOptions()
    service = webdriver.ChromeService("/opt/chromedriver")

    options.binary_location = '/opt/chrome/chrome'
    options.add_argument("--headless=new")
    options.add_argument('--no-sandbox')
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280x1696")
    options.add_argument("--single-process")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-dev-tools")
    options.add_argument("--no-zygote")
    options.add_argument(f"--user-data-dir={mkdtemp()}")
    options.add_argument(f"--data-path={mkdtemp()}")
    options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    options.add_argument("--remote-debugging-port=9222")

    driver = webdriver.Chrome(options=options, service=service)
    action = ActionChains(driver)

    return driver, action

def get_optimal_route(r_e):
    remove_keywords = ['최적', '최소도보', '최소환승', '최소시간','다음날']
    final_route = None
    walk_10_flag = False
    over_1am = False
    for_start = 4
    route_mini = []
    w10sq = []
    r = []

    current_hour = time.localtime().tm_hour
    if 1 <= current_hour < 5:
        over_1am = True

    for i in r_e:
        r.append(i.get_attribute("innerText").split('\n'))

    for i in r:
            if i[0] in remove_keywords:
                i.pop(0)
            if i[1] in remove_keywords:
                i.pop(1)
            
    for i in r:
        list_a = []
        for j in range(3,len(i),2):
            if '분' == i[j+1][-1]:
                list_a.append([i[j], int(i[j+1][:-1])])
            else:
                break
        route_mini.append(list_a)
    
    route_mini_sorted = sorted(route_mini, key=len)
    if debuging_mode:
        print(r)
        print(route_mini)
        print(route_mini_sorted)
    for i in route_mini_sorted:
        for j in i:
            if j[0] == '도보':
                if j[1] >= 10:
                    final_route = i
                    walk_10_flag = True
                    w10sq.append(i.index(j))

        if walk_10_flag:
            break    

    if walk_10_flag:
        route_seq = route_mini.index(final_route)
    else:
        route_seq = 0
    
    return (route_seq,w10sq,route_mini[route_seq])

def make_detail_route(w10sq,route,r_e,r_sq,driver,action):

    action.move_to_element(r_e[r_sq]).perform()
    r_e[r_sq].click()
    r_e[r_sq].click()
    d_r_r = []
    d_t_r = []

    WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.XPATH, '//div[@class="summary_area"]')))
    d_r_r = driver.find_elements(By.XPATH, '//strong[@class = "path_title"]')
    d_t_r = driver.find_elements(By.XPATH, '//div[@class = "detail_step_icon_area"]')
    print(d_t_r)
    d_t = []
    d_r = []
    replace_walk_pair = []
    
    if debuging_mode:
        print(route)

    for i in d_r_r:
        d_r.append(i.get_attribute("innerText"))
    for i in d_t_r:
        d_t.append(f'{i.get_attribute("innerText").replace('\n',' ')}')
    print(d_t)

    for i in range(len(d_r)):
        if '승차' in d_r[i]:
            d_r[i] = d_r[i].split('승차')[0].strip()
        elif '하차' in d_r[i]:
            d_r[i] = d_r[i].split('하차')[0].strip()
    seen = set()
    i = 0

    while i < len(d_r):
        if d_r[i] in seen:
            d_r.pop(i)
        else:
            seen.add(d_r[i])
            i += 1
    print(w10sq)
    if route[0][0] != '도보':
        d_r.pop(0)
        len_d_r = len(d_r) -1
        route_seq_list = [0] * len_d_r
        print(route_seq_list)
        if debuging_mode:
            print(route)

        try:
            for i in w10sq:
                replace_walk_pair.append([d_r[i],d_r[i+1]])
                print(i)
                route_seq_list[i] = 1
        except IndexError:
            replace_walk_pair = []

    elif route[-1][0] != '도보':
        d_r.pop(-1)
        len_d_r = len(d_r) -1
        route_seq_list = [0] * len_d_r

        try:
            for i in w10sq:
                replace_walk_pair.append([d_r[i],d_r[i+1]])
                route_seq_list[i] = 1
        except IndexError:
            replace_walk_pair = []

    else:
        len_d_r = len(d_r) -1
        route_seq_list = [0] * len_d_r

        try:
            for i in w10sq:
                replace_walk_pair.append([d_r[i],d_r[i+1]])
                route_seq_list[i] = 1
        except IndexError:
            replace_walk_pair = []
    print(d_t,'!!!')
    return(d_r,d_t,replace_walk_pair,route_seq_list)

def make_ddareuungi_route(replace_walk_pair,w10sq,route_seq_list):
    start_bike_s = []
    end_bike_s = []
    start_bike_info = []
    end_bike_info = []
    counter_1 = 0

    for i in replace_walk_pair:
        ws_x,ws_y = get_x_y(i[0])
        we_x,we_y = get_x_y(i[1])
        bs_s = find_Ddareuungi_station(float(ws_y),float(ws_x))
        bs_e = find_Ddareuungi_station(float(we_y),float(we_x))
        if bs_s != 0 and bs_e != 0:
            start_bike_s.append(bs_s)
            end_bike_s.append(bs_e)
        else:
            del_ = w10sq[counter_1]

            del w10sq[counter_1]
            route_seq_list[del_] = 0
            continue
        counter_1 += 1

    for i in start_bike_s:
            adress = reverse_geo(i[1],i[2])
            start_bike_info.append([i[0],adress,i[4],i[5]])

    for i in end_bike_s:
            adress = reverse_geo(i[1],i[2])
            end_bike_info.append([i[0],adress,i[4],i[5]])

    return(start_bike_info,end_bike_info,route_seq_list)

def make_final_route(route_seq_list, detail_route, detail_transport, start_bike_info, end_bike_info):
    final_route = []
    trans_count = 0
    bike_count = 0
    route_count = 0
    repeat_count = 0

    for i in range(len(detail_route) + len(route_seq_list)):
        if i % 2 == 0 or i == 0:
            final_route.append(detail_route[route_count])
            route_count += 1
        else:
            try:
                if route_seq_list[repeat_count] == 0:
                    final_route.append(detail_transport[trans_count])
                    trans_count += 1
                else:
                    final_route.append(f"도보 {start_bike_info[bike_count][3]}m")
                    final_route.append(f"{start_bike_info[bike_count][0]} ({start_bike_info[bike_count][1]}) 잔여대수 : {start_bike_info[bike_count][2]}대")
                    final_route.append("따릉이 이동")
                    final_route.append(f"{end_bike_info[bike_count][0]} ({end_bike_info[bike_count][1]})")
                    final_route.append(f"도보 {end_bike_info[bike_count][3]}m")
                    bike_count += 1
                repeat_count += 1
            except:
                return(final_route)

    return(final_route)

def make_route(start_input, end_input,driver,action):
    start_x, start_y = get_x_y_ep(start_input)
    end_x, end_y = get_x_y_ep(end_input)

    driver.get(f"https://map.naver.com/p/directions/{start_x},{start_y},{start_input}/{end_x},{end_y},{end_input}/-/transit?")
    try:
        WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.XPATH, '//div[@class = "item_btn"]')))
    except:
        final_route = '이용 가능한 대중교통이 없는 구간 입니다, 다른 출발지, 목적지를 입력해주세요'
        return(final_route)
    route_elements = driver.find_elements(By.XPATH, '//div[@class = "item_btn"]')

    route_seq, walk_10_seq,route = get_optimal_route(route_elements)

    if not route:
        final_route = "해당 범위는 아직 지원하지 않습니다, 다른 출발지, 목적지를 입력해주세요"
        return(final_route)
        
    detail_route, detail_transport_f, replace_walk_pair, route_seq_list_f = make_detail_route(walk_10_seq,route,route_elements,route_seq,driver,action)


    if able_bike:
        start_bike_info, end_bike_info,route_seq_list = make_ddareuungi_route(replace_walk_pair,walk_10_seq,route_seq_list_f)
        if debuging_mode:
            print(start_bike_info, end_bike_info)
    else:
        start_bike_info,end_bike_info,replace_walk_pair,detail_route,route_seq_list = reset(start_bike_info,end_bike_info,replace_walk_pair,detail_route,route_seq_list)

    if 1 in route_seq_list:  
        if not start_bike_info:
            len_d_r = len(detail_route) -1
            route_seq_list = [0] * len_d_r

    if 1 not in route_seq_list:
        detail_route, detail_transport, replace_walk_pair, route_seq_list = make_detail_route(walk_10_seq,route,route_elements,0,driver,action)
        start_bike_info,end_bike_info,replace_walk_pair,detail_route,route_seq_list = reset(start_bike_info,end_bike_info,replace_walk_pair,detail_route,route_seq_list)
        final_route = make_final_route(route_seq_list, detail_route, detail_transport, start_bike_info, end_bike_info)
        return(final_route)


    detail_transport = []

    try:
        for i in range(len(route_seq_list)):
            if route_seq_list[i] == 0:
                detail_transport.append(detail_transport_f[i])
    except IndexError:
        pass


    if debuging_mode:
        print(walk_10_seq, detail_route, detail_transport, replace_walk_pair, route_seq_list,start_bike_info,end_bike_info)
    try:
        final_route = make_final_route(route_seq_list, detail_route, detail_transport, start_bike_info, end_bike_info)
    except:
        final_route = "해당 범위는 아직 지원하지 않습니다, 다른 출발지, 목적지를 입력해주세요"
    return(final_route)

def reset(start_bike_info,end_bike_info,replace_walk_pair,detail_route,route_seq_list):
    start_bike_info =[]
    end_bike_info = []
    replace_walk_pair = []
    len_d_r = len(detail_route) -1
    route_seq_list = [0] * len_d_r
    return(start_bike_info,end_bike_info,replace_walk_pair,detail_route,route_seq_list)


def make_listcard_list(final_route):
    listcard = []
    for i in range(0,len(final_route),2):
        if i == (len(final_route)-1):
            append_m = {
                    "title": final_route[i],
                    "description": "도착"
                    }
        else:
            append_m = {
                        "title": final_route[i],
                        "description": f"{final_route[i+1]}\n >>{final_route[i+2]}"
                        }
            
        listcard.append(append_m)

    return(listcard)

t_map_api_key = 'n8zsIWsyk34hbmYfX4PzbjN4CKizkXD3FdvGi5ig'

def t_map_header():
    headers = {
    'appKey': t_map_api_key,
    'Content-Type': 'application/json'
    }
    return(headers)

def get_x_y(keyword):
    x_y_url = 'https://apis.openapi.sk.com/tmap/pois'
    headers = t_map_header()
    keyword_e = keyword.encode('utf-8')

    x_y_params = {
        'version': 1,
        'searchKeyword': keyword_e,
        'searchType': 'all',
    }

    x_y_response = requests.get(x_y_url, headers=headers, params=x_y_params)
    try:
        x_y_data = x_y_response.json()

        x = x_y_data['searchPoiInfo']['pois']['poi'][0]['newAddressList']['newAddress'][0]['centerLon']
        y = x_y_data['searchPoiInfo']['pois']['poi'][0]['newAddressList']['newAddress'][0]['centerLat']
        return(x, y)
    except:
        return(0,0)

def get_x_y_ep(keyword):
    x_y_url = 'https://apis.openapi.sk.com/tmap/pois'
    headers = t_map_header()
    keyword_e = keyword.encode('utf-8')

    x_y_params = {
        'version': 1,
        'searchKeyword': keyword_e,
        'searchType': 'all',
        'resCoordType': 'EPSG3857'
    }

    x_y_response = requests.get(x_y_url, headers=headers, params=x_y_params)
    try:
        x_y_data = x_y_response.json()

        x = x_y_data['searchPoiInfo']['pois']['poi'][0]['newAddressList']['newAddress'][0]['centerLon']
        y = x_y_data['searchPoiInfo']['pois']['poi'][0]['newAddressList']['newAddress'][0]['centerLat']
        return(x, y)
    except:
        return(0,0)

def find_Ddareuungi_station(lat, lon, radius=1):
    Ddareuungi_url_1 = 'http://openapi.seoul.go.kr:8088/545666646e6169643833456d794e4d/json/bikeList/1/1000/'
    Ddareuungi_url_2 = 'http://openapi.seoul.go.kr:8088/545666646e6169643833456d794e4d/json/bikeList/1001/2000/'

    Ddareuungi_response_1 = requests.get(Ddareuungi_url_1)
    Ddareuungi_response_2 = requests.get(Ddareuungi_url_2)

    Ddareuungi_data_1 = Ddareuungi_response_1.json()
    Ddareuungi_data_2 = Ddareuungi_response_2.json()

    station_list = Ddareuungi_data_1['rentBikeStatus']['row'] + Ddareuungi_data_2['rentBikeStatus']['row']

    station_result = []
    for i in station_list:
        s_lat = float(i['stationLatitude'])
        s_lon = float(i['stationLongitude'])
        dis_gap = haversine((lat, lon), (s_lat, s_lon))
        if dis_gap <= radius:
            if int(i['parkingBikeTotCnt']) > 0:
                if i not in station_result:
                    station_result.append([i['stationName'],i['stationLatitude'],i['stationLongitude'],i['stationId'],int(i['parkingBikeTotCnt']),float(f"{dis_gap*1000:.1f}")])
    
    radius_stations = sorted(station_result, key=lambda x: x[5])
    try:
        return radius_stations[0]
    except:
        return 0
    
def reverse_geo(lat,lon):
    r_geo_url = 'https://apis.openapi.sk.com/tmap/geo/reversegeocoding'
    headers = t_map_header()

    r_geo_parms = {
        'version': 1,       
        'lon' : lon,
        'lat' : lat,
        'addressType' : 'A02'
    }

    r_geo_response = requests.get(r_geo_url, headers=headers, params=r_geo_parms)
    r_geo_data = r_geo_response.json()

    return(r_geo_data['addressInfo']['fullAddress'])