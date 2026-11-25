import asyncio

# Các khóa dùng chung trong một tiến trình NLP Server.
mcu_locks = {}
device_locks = {} # ngăn nhiều request tới đồng thời 1 device


def get_mcu_lock(mcu_id: int):
    # nếu chưa lock thì tạo lock mới
    if mcu_id not in mcu_locks:
        mcu_locks[mcu_id] = asyncio.Lock() # trả về class quản lý khóa bất đồng bộ

    return mcu_locks[mcu_id]


def get_device_lock(device_id: int):
    # nếu chưa có lock thì tạo mới mới
    if device_id not in device_locks:
        device_locks[device_id] = asyncio.Lock()
        
    return device_locks[device_id]
