import datetime

import requests

APP_ID = "cli_a969f2762cb81ccb"
APP_SECRET = "EZJA8DcyTwsBnFiuXuwYygLUSYlvcHsZ"
APP_TOKEN = "MOUwbKzNOaIOYisW5UocW2Q1nYf"
TABLE_ID = "tblCald7kfQqQmDt"

session = requests.Session()
session.trust_env = False
session.proxies = {
    "http": None,
    "https": None,
}


def convert_publication_date_to_timestamp(publication_date):
    if publication_date is None:
        return None

    if isinstance(publication_date, (int, float)):
        return int(publication_date)

    if isinstance(publication_date, datetime.date):
        publication_datetime = datetime.datetime.combine(
            publication_date,
            datetime.time.min,
            tzinfo=datetime.timezone(datetime.timedelta(hours=8)),
        )
        return int(publication_datetime.timestamp() * 1000)

    if isinstance(publication_date, str):
        try:
            publication_datetime = datetime.datetime.strptime(
                publication_date[:10],
                "%Y-%m-%d",
            ).replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
            return int(publication_datetime.timestamp() * 1000)
        except ValueError:
            return None

    return None


def get_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal/"
    res = session.post(
        url,
        json={
            "app_id": APP_ID,
            "app_secret": APP_SECRET,
        },
        timeout=20,
    )
    print("get_token status:", res.status_code)
    print("get_token body:", res.text)
    res.raise_for_status()
    data = res.json()
    if "tenant_access_token" not in data:
        raise Exception(f"获取 token 失败: {data}")
    return data["tenant_access_token"]


def get_records(token):
    url = (
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}"
        f"/tables/{TABLE_ID}/records/search"
    )
    headers = {
        "Authorization": f"Bearer {token}"
    }

    records = []
    page_token = None

    while True:
        payload = {}
        if page_token:
            payload["page_token"] = page_token

        res = session.post(url, headers=headers, json=payload, timeout=20)
        print("get_records status:", res.status_code)
        print("get_records body:", res.text)
        res.raise_for_status()

        data = res.json()
        items = data.get("data", {}).get("items", [])
        records.extend(items)

        page_token = data.get("data", {}).get("page_token")
        if not page_token:
            break

    return records


def get_existing_links(token):
    existing_links = set()

    for item in get_records(token):
        fields = item.get("fields", {})
        link_value = fields.get("公告链接")

        if isinstance(link_value, dict):
            link = link_value.get("link") or link_value.get("text")
        else:
            link = link_value

        if link:
            existing_links.add(link)

    print(f"已有记录数: {len(existing_links)}")
    return existing_links


def add_record(token, item):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    publication_timestamp = convert_publication_date_to_timestamp(item["发布时间"])
    if publication_timestamp is None:
        raise ValueError(f"发布时间无法转换为时间戳: {item['发布时间']}")

    data = {
        "fields": {
            "公告标题": item["公告标题"],
            "发布时间": publication_timestamp,
            "公告链接": {
                "link": item["公告链接"],
                "text": item["公告链接"]
            },
            "发布机关": item["发布机关"],
            "当前状态": "未看",
        }
    }

    res = session.post(url, headers=headers, json=data, timeout=20)
    print("add_record status:", res.status_code)
    print("add_record body:", res.text)
    res.raise_for_status()


def update_record(token, record_id):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{APP_TOKEN}/tables/{TABLE_ID}/records/{record_id}"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "fields": {
            "当前状态": "已截止"
        }
    }
    res = session.put(
        url,
        headers=headers,
        json=payload,
        timeout=20,
    )
    print("update_record status:", res.status_code)
    print("update_record body:", res.text)
    res.raise_for_status()