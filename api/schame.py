from pydantic import BaseModel
from typing import List,Dict,Optional


#umami响应参数
class Umami_resp(BaseModel):
    today_uv: int = None
    today_pv: int = None
    yesterday_uv: int = None
    yesterday_pv: int = None
    last_month_pv: int = None
    last_year_pv: int = None

class KVConfig(BaseModel):
    url: str
    rest_api_url: str
    rest_api_token: str
    rest_api_read_only_token: str

class Opts(BaseModel):
    ex: Optional[int]
    px: Optional[int]
    exat: None
    pxat: None
    keepTtl: None