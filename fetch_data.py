# import requests
# from product import Product
# from config import URL_LIST
#
# def fetch_product_data(url, timeout=10):
#     """Lấy dữ liệu sản phẩm từ API."""
#     try:
#         response = requests.get(url, timeout=timeout)
#         response.raise_for_status()
#         return response.json()
#     except requests.RequestException as e:
#         print(f"Lỗi khi tải dữ liệu từ {url}: {e}")
#     return None
#
# def load_products():
#     """Tải danh sách sản phẩm từ nhiều URL, loại bỏ trùng lặp và sắp xếp theo giảm giá."""
#     unique_products = set()
#     for url in URL_LIST:
#         data = fetch_product_data(url)
#         if data:
#             product_list = data.get("response", {}).get("resultData", {}).get("productList", [])
#             for p in product_list:
#                 category = p.get("categorySubTypeEngName", "")
#                 if category == "Washing Machines Accessories":
#                     continue
#                 for model in p.get("modelList", []):
#                     product = Product(
#                         model.get("displayName"), model.get("formattedPriceSave"), model.get("modelCode"),
#                         model.get("originPdpUrl"), model.get("pdpUrl"), model.get("price"),
#                         model.get("priceDisplay"), model.get("promotionPrice"), model.get("ctaType"),
#                         model.get("pviSubtypeName"), category
#                     )
#                     unique_products.add(product)
#
#     return sorted(unique_products, key=lambda x: (-x.get_discount_percentage(), x.price, x.get_cta_display() != "Còn hàng"))
