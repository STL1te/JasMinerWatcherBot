import time
import requests

from requests.auth import HTTPDigestAuth
from datetime import timedelta


class JasMiner(object):

    minerName = ''
    firmwareVersion = ''
    uptime = 0
    hashrate = ''
    avg_hashrate = ''
    fans = []
    boards_stats = []

    @staticmethod
    def create_from_data(data):
        miner = JasMiner()
        miner.__update(data)
        return miner

    def __update(self, data):
        self.minerName = data['summary']['miner']
        self.firmwareVersion = data['summary']['version']
        self.uptime = self.__get_human_uptime(data['summary']['uptime'])
        self.hashrate = data['summary']['rt']
        self.avg_hashrate = data['summary']['avg']
        self.fans = self.__get_fans_info(data)
        self.boards_stats = self.__get_boards_stats(data)

    def __get_human_uptime(self, uptime):
        delta = timedelta(seconds=uptime)
        human_str = ''

        if delta.days > 0:
            human_str = f'{delta.days}d'

        mm, ss = divmod(delta.seconds, 60)
        hh, mm = divmod(mm, 60)

        if hh > 0:
            human_str += '%dh' % hh
        if mm > 0:
            human_str += '%02dm' % mm
        human_str += '%02ds' % ss

        return human_str

    def __get_fans_info(self, data):
        boards = data['boards']
        fan_num = boards['fan_num']
        fans = []

        for i in range(fan_num):
            fan_idx = i + 1
            key_rpm = f'fan{fan_idx}'
            key_percent = f'fan_percent{fan_idx}'
            rpm = boards.get(key_rpm, 0)
            percent = boards.get(key_percent, '0')

            if rpm != 0:
                fans.append((rpm, percent + '%'))

        return fans

    def __get_boards_stats(self, data):
        boards = data['boards']['board']
        result = []

        for board in boards:
            asics = board['asics']
            boards_temps = []

            for i in range(asics):
                key_temp = f'asic{i}_temp'
                boards_temps.append(board.get(key_temp, 0))

            result.append((board['asic_stat'], boards_temps))

        return result


class JasMinerApi:

    def __init__(self, host, user="root", password="root"):
        if host.startswith('http'):
            self.__url = host
        else:
            self.__url = f"http://{host}"

        self.__user = user
        self.__password = password
        self.__session = self.__connect()

    @property
    def is_connected(self):
        return self.__session is not None

    def __connect(self):
        session = requests.Session()
        session.auth = HTTPDigestAuth(self.__user, self.__password)

        req = session.get(self.__url)
        if req.status_code == 200:
            return session

    def get_miner_data(self) -> JasMiner:
        if self.is_connected:
            endpoint = "/cgi-bin/minerStatus_all.cgi"
            data = self.__call_api(endpoint)
            return JasMiner.create_from_data(data)

    def __call_api(self, endpoint):
        if self.__session is None:
            print("No connection to API!")
            return

        req_count = 20
        while req_count > 0:
            req = self.__session.get(self.__url + endpoint, params={"_": int(time.time())})
            req_count -= 1

            if req.status_code == 200:
                return req.json()
            elif req.status_code == 401:
                self.__session = self.__connect()
                req_count = 20

            time.sleep(1)

        raise Exception("API is not available!")


if __name__ == '__main__':
    miners = ['192.168.1.70', '192.168.1.71', '192.168.1.72', '192.168.1.73']

    for miner_host in miners:
        api = JasMinerApi(miner_host)
        print(api.is_connected)
        miner = api.get_miner_data()
        print(miner.__dict__)


