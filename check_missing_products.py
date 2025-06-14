import sqlite3
import requests
from price_history import DB_NAME

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

    # In ra các sản phẩm thỏa mãn điều kiện
    if missing_products:
        print("Các sản phẩm có trong database nhưng không có trong API:")
        for model_code, displayName in missing_products:
            print(f"Model Code: {model_code}, Display Name: {displayName}")
    else:
        print("Không có sản phẩm nào thỏa mãn điều kiện.")

if __name__ == "__main__":
    main()