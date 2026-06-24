from db import update_stock, get_stock

def simulate_consumption(item="starter_maggot", consumption_rate=1.5):
    """
    Kurangi stok sebesar consumption_rate setiap panggilan.
    Return True jika stok berubah, False jika sudah <= 0.
    """
    stock, _, _ = get_stock(item)
    if stock <= 0:
        return False
    new_stock = max(0, stock - consumption_rate)
    update_stock(item, new_stock)
    return True