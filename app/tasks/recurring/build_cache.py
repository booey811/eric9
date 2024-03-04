# run_cache.py
from app.cache.utilities import build_product_cache, build_device_cache, build_pre_check_cache, build_part_cache

if __name__ == "__main__":
    build_product_cache()
    build_device_cache()
    build_pre_check_cache()
    build_part_cache()
