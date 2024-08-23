from fastapi import APIRouter,HTTPException
from server.schame import Umami_resp,KVConfig,Opts
import requests
import json
import os
import time

#获取并构建umami相关参数
umami_token = os.environ.get("umami_token")
umami_web_id = os.environ.get("umami_web_id")
umami_url = os.environ.get("umami_url")

cache_time = 600  # 缓存时间为10分钟（600秒）

# 获取当前时间戳（毫秒级）
current_timestamp = int(time.time() * 1000)

# Umami API 的起始时间戳（毫秒级）
start_timestamp_today = int(time.mktime(time.strptime(time.strftime('%Y-%m-%d'), '%Y-%m-%d')) * 1000)
start_timestamp_yesterday = int(time.mktime(time.strptime(time.strftime('%Y-%m-%d', time.localtime(time.time() - 86400)), '%Y-%m-%d')) * 1000)
start_timestamp_last_month = int(time.mktime(time.strptime(time.strftime('%Y-%m', time.localtime(time.time() - 2592000)) + '-01', '%Y-%m-%d')) * 1000)
start_timestamp_last_year = int(time.mktime(time.strptime(time.strftime('%Y', time.localtime(time.time() - 31536000)) + '-01-01', '%Y-%m-%d')) * 1000)


# 定义 Umami API 请求函数
def fetch_umami_data(umami_url, website_id, start_at, end_at, umami_token):
    url = f"{umami_url}/api/websites/{website_id}/stats"
    headers = {
        "Authorization": f"Bearer {umami_token}",
        "Content-Type": "application/json"
    }
    params = {
        'startAt': start_at,
        'endAt': end_at
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching data: {e}")

from typing import Optional

class KV:
    def __init__(self, kv_config: Optional[KVConfig] = None):
        if kv_config is None:
            self.kv_config = KVConfig(
                url=os.environ.get('KV_URL'),
                rest_api_url=os.environ.get("KV_REST_API_URL"),
                rest_api_token=os.environ.get("KV_REST_API_TOKEN"),
                rest_api_read_only_token=os.environ.get(
                    "KV_REST_API_READ_ONLY_TOKEN"
                ),
            )
        else:
            self.kv_config = kv_config
    
    def set(self, key, value, opts: Optional[Opts] = None) -> bool:
            headers = {
                'Authorization': f'Bearer {self.kv_config.rest_api_token}',
            }

            url = f'{self.kv_config.rest_api_url}/set/{key}'

            if opts is not None and opts.ex is not None:
                url = f'{url}/ex/{opts.ex}'
            try:
                resp = requests.post(url, headers=headers,json=value)
                resp.raise_for_status()
                return resp.json()['result']
            except requests.exceptions.RequestException as e:
                raise HTTPException(status_code=500, detail=f"Failure to store data: {e}")


    def get(self, key) -> bool:
            headers = {
                'Authorization': f'Bearer {self.kv_config.rest_api_token}',
            }
            try:
                resp = requests.get(f'{self.kv_config.rest_api_url}/get/{key}', headers=headers)
                resp.raise_for_status()
                return resp.json()['result']
            except requests.exceptions.RequestException as e:
                raise HTTPException(status_code=500, detail=f"Failure to get data: {e}")


kv = KV()

router = APIRouter()

#umami统计接口
@router.get("/umami-stats",response_model=Umami_resp)
async def umami():
    # 检查缓存
    kv_cache_time = kv.get("cache_time") 
    #判断缓存是否超过10分钟
    if (kv_cache_time and int(time.time()) - int(kv_cache_time) < cache_time):
        cached_data = kv.get('umami_cache')
        if cached_data:
            cahce_json = json.loads(cached_data)
            return Umami_resp(**cahce_json)

    # 获取统计数据
    today_data = fetch_umami_data(umami_url, umami_web_id, start_timestamp_today, current_timestamp, umami_token)
    yesterday_data = fetch_umami_data(umami_url,umami_web_id, start_timestamp_yesterday, start_timestamp_today, umami_token)
    last_month_data = fetch_umami_data(umami_url,umami_web_id, start_timestamp_last_month, current_timestamp, umami_token)
    last_year_data = fetch_umami_data(umami_url, umami_web_id, start_timestamp_last_year, current_timestamp, umami_token)

    # 组装返回的 JSON 数据
    response_data = {
            "today_uv": today_data.get('visitors', {}).get('value') if today_data else None,
            "today_pv": today_data.get('pageviews', {}).get('value') if today_data else None,
            "yesterday_uv": yesterday_data.get('visitors', {}).get('value') if yesterday_data else None,
            "yesterday_pv": yesterday_data.get('pageviews', {}).get('value') if yesterday_data else None,
            "last_month_pv": last_month_data.get('pageviews', {}).get('value') if last_month_data else None,
            "last_year_pv": last_year_data.get('pageviews', {}).get('value') if last_year_data else None
        }
    #存储当前时间戳（秒级）
    kv.set(key='cache_time', value=int(time.time()))
    #存入数据
    kv.set(key='umami_cache', value=response_data)

    return Umami_resp(**response_data)