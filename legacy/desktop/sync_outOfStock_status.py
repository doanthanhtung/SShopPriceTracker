import sqlite3
import requests
from price_history import DB_NAME
from datetime import datetime

URL_LIST = [
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=01010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=01020000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=01030000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=04010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08030000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=07010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08050000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08080000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08040000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=08070000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=09010000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
    "https://searchapi.samsung.com/v6/front/epp/v2/product/finder/global?type=01040000&siteCode=vn&start=1&num=99&sort=newest&onlyFilterInfoYN=N&keySummaryYN=N&companyCode=srv&pfType=G",
]


def fetch_product_data(url, timeout=10):
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Có lỗi xảy ra khi lấy dữ liệu từ {url}: {e}")
        return None


def get_api_products():
    api_model_codes = []
    for url in URL_LIST:
        data = fetch_product_data(url)
        if data:
            product_list = data.get("response", {}).get("resultData", {}).get("productList", [])
            for p in product_list:
                if p.get("categorySubTypeEngName", "") == "Washing Machines Accessories":
                    continue
                for model in p.get("modelList", []):
                    model_code = model.get("modelCode")
                    if model_code:
                        api_model_codes.append(model_code)
    return api_model_codes


def get_all_database_products():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT model_code, displayName
        FROM price_history
        """
    )
    products = cursor.fetchall()
    conn.close()
    return products


def get_latest_ctaType(model_code):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ctaType
        FROM price_history
        WHERE model_code = ? AND date = (SELECT MAX(date) FROM price_history WHERE model_code = ?)
        """,
        (model_code, model_code)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def update_ctaType_to_outOfStock(model_code, displayName):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    # Lấy giá và ctaType mới nhất (nếu có)
    cursor.execute(
        """
        SELECT price, ctaType
        FROM price_history
        WHERE model_code = ? AND date = (SELECT MAX(date) FROM price_history WHERE model_code = ?)
        """,
        (model_code, model_code)
    )
    result = cursor.fetchone()
    price = result[0] if result else 0
    current_ctaType = result[1] if result else None

    # Chỉ cập nhật nếu ctaType mới nhất khác "outOfStock"
    if current_ctaType != "outOfStock":
        cursor.execute(
            """
            INSERT OR REPLACE INTO price_history (model_code, displayName, date, price, ctaType)
            VALUES (?, ?, ?, ?, ?)
            """,
            (model_code, displayName, today, price, "outOfStock")
        )
        conn.commit()
        print(f"Đã cập nhật ctaType của {model_code} ({displayName}) thành 'outOfStock'")
    # else:
    #     print(f"Bỏ qua {model_code} ({displayName}) vì ctaType mới nhất đã là 'outOfStock'")

    conn.close()


def main():
    # Lấy danh sách model_code từ API
    api_model_codes = get_api_products()

    # Lấy tất cả sản phẩm từ database
    db_products = get_all_database_products()

    # Tìm các sản phẩm có trong database nhưng không có trong API
    missing_products = []
    for model_code, displayName in db_products:
        if model_code not in api_model_codes:
            missing_products.append((model_code, displayName))

    # In ra và cập nhật ctaType cho các sản phẩm thỏa mãn
    if missing_products:
        # print("Các sản phẩm có trong database nhưng không có trong API:")
        for model_code, displayName in missing_products:
            # print(f"Model Code: {model_code}, Display Name: {displayName}")
            update_ctaType_to_outOfStock(model_code, displayName)
    else:
        print("Không có sản phẩm nào thỏa mãn điều kiện.")


if __name__ == "__main__":
    main()