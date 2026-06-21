import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# Nominatim は無料の地図サービス（OpenStreetMap）を使って住所→座標を変換する
# user_agent にはアプリ固有の名前を設定する（Nominatim の利用規約要件）
_geolocator = Nominatim(user_agent="chiikawa-stock-tracker-v1")


def address_to_coords(address: str) -> tuple[float, float] | tuple[None, None]:
    """
    住所文字列を緯度・経度に変換して返す。
    変換できなかった場合は (None, None) を返す。

    例: "東京都渋谷区道玄坂1丁目" → (35.658, 139.701)
    """
    try:
        # Nominatim の利用規約: 1秒以上の間隔を空けること
        time.sleep(1)
        location = _geolocator.geocode(address, language="ja", timeout=10)
        if location:
            return location.latitude, location.longitude
        return None, None
    except GeocoderTimedOut:
        return None, None
