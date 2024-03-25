import json
import schedule
import time
import os

from jasminer_api import JasMinerApi
from utils import db_connect
from config import MINER_DATA_PATH


class Updater:

    def __init__(self):
        self.__miners_data = self.__load_data()

    def __load_data(self):
        if not os.path.exists(MINER_DATA_PATH):
            return {}

        with open(MINER_DATA_PATH, 'r') as f:
            return json.load(f)

    def __save_data(self):
        with open(MINER_DATA_PATH, 'w') as f:
            json.dump(self.__miners_data, f, indent=4)

    def check_updates(self):
        with db_connect() as connect:
            cursor = connect.cursor()
            sql = """SELECT id, minerName, host, user, password FROM devices"""
            select_db = cursor.execute(sql)

            for miner_id, minerName, host, user, password in select_db.fetchall():
                api = JasMinerApi(host, user, password)
                if api.is_connected:
                    try:
                        data = api.get_miner_data()
                        self.__miners_data[miner_id] = {
                            'id': miner_id,
                            'minerUserName': minerName,
                            'minerModel': data.minerName,
                            'firmwareVersion': data.firmwareVersion,
                            'uptime': data.uptime,
                            'hashrate': data.hashrate,
                            'avg_hashrate': data.avg_hashrate,
                            'fans': data.fans,
                            'boards_stats': data.boards_stats,
                        }
                    except Exception as e:
                        print('Can\'t update miner data')

            self.__save_data()


if __name__ == '__main__':
    upd = Updater()
    upd.check_updates()

    schedule.every(30).seconds.do(upd.check_updates)

    while True:
        schedule.run_pending()
        time.sleep(1)
