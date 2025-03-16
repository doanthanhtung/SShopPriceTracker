# import html
#
# class Product:
#     """Lớp đại diện cho sản phẩm."""
#
#     def __init__(self, displayName, formattedPriceSave, modelCode, originPdpUrl, pdpUrl,
#                  price, priceDisplay, promotionPrice, ctaType, pviSubtypeName, categorySubTypeEngName):
#         self.displayName = html.unescape(displayName)
#         self.formattedPriceSave = formattedPriceSave
#         self.modelCode = modelCode
#         self.originPdpUrl = originPdpUrl
#         self.pdpUrl = pdpUrl
#         self.price = float(price) if price else 0
#         self.priceDisplay = priceDisplay
#         self.promotionPrice = float(promotionPrice) if promotionPrice else 0
#         self.ctaType = ctaType
#         self.pviSubtypeName = pviSubtypeName
#         self.categorySubTypeEngName = categorySubTypeEngName
#
#     def __eq__(self, other):
#         return isinstance(other, Product) and self.modelCode == other.modelCode
#
#     def __hash__(self):
#         return hash(self.modelCode)
#
#     def get_discount_percentage(self):
#         if self.price > 0 and self.promotionPrice > 0:
#             return round((1 - self.promotionPrice / self.price) * 100, 2)
#         return 0
#
#     def get_cta_display(self):
#         return "Hết hàng" if self.ctaType == "outOfStock" else "Còn hàng"
