import requests

def fetch_product_data(url, timeout=10):
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.ConnectionError:
        print("Không thể kết nối đến mạng. Vui lòng kiểm tra kết nối internet.")
    except requests.Timeout:
        print("Request quá thời gian chờ. Vui lòng thử lại.")
    except requests.RequestException as e:
        print(f"Có lỗi xảy ra: {e}")
    return None
