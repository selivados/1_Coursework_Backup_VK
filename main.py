import json
import os
import shutil
import time

import requests
from tqdm import tqdm


class VKontakte:
    url = 'https://api.vk.com/method/'

    def __init__(self, token):
        self.params = {
            'access_token': token,
            'v': '5.131'
        }

    def get_avatar_photos(self, user_id, count=5):
        request_url = self.url + 'photos.get'
        params = {
            'owner_id': user_id,
            'album_id': 'profile',
            'rev': 1,
            'extended': 1,
            'count': count
        }
        response = requests.get(request_url, params={**self.params, **params}).json()
        return response['response']['items']

    def get_all_photos(self, user_id):
        request_url = self.url + 'photos.getAll'
        photos = []
        offset = 0
        count = 200
        while True:
            params = {
                'owner_id': user_id,
                'extended': 1,
                'offset': offset,
                'count': count
            }
            response = requests.get(request_url, params={**self.params, **params}).json()
            photos.extend(response['response']['items'])
            photos_total_count = response['response']['count']
            if offset + count >= photos_total_count:
                break
            offset += count
            time.sleep(0.33)
        return photos


class YandexDisk:
    url = 'https://cloud-api.yandex.net/v1/disk/'

    def __init__(self, token):
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'OAuth {token}'
        }

    def _get_upload_url(self, yd_file_path):
        request_url = self.url + 'resources/upload'
        params = {'path': yd_file_path}
        response = requests.get(request_url, headers=self.headers, params=params).json()
        return response['href']

    def _get_operation_status(self, status_link, time_sleep):
        response = requests.get(status_link, headers=self.headers).json()
        while response['status'] == 'in-progress':
            time.sleep(time_sleep)
            response = requests.get(status_link, headers=self.headers).json()
        return response['status']

    def create_folder(self, yd_folder_path):
        request_url = self.url + 'resources'
        params = {'path': yd_folder_path}
        response = requests.put(request_url, headers=self.headers, params=params)
        if response.status_code == 201:
            print(f"\nПапка '{yd_folder_path}' успешно создана на Яндекс.Диске")
        time.sleep(0.1)
        return yd_folder_path

    def upload_file_from_pc(self, pc_file_path, yd_file_path):
        upload_url = self._get_upload_url(yd_file_path)
        with open(pc_file_path, 'rb') as data:
            response = requests.put(upload_url, data=data)
        return response.status_code

    def upload_photos_from_pc_folder(self, pc_folder_path, yd_folder_path):
        file_names = os.listdir(pc_folder_path)
        json_data = []
        count = 0
        for file_name in tqdm(file_names, desc='Загрузка фотографий на Яндекс.Диск', ncols=100):
            status_code = self.upload_file_from_pc(
                pc_file_path=f'{pc_folder_path}/{file_name}',
                yd_file_path=f'{yd_folder_path}/{file_name[:-6]}.jpg'
            )
            if status_code == 201:
                json_info = {
                    'file_name': f'{file_name[:-6]}.jpg',
                    'size': file_name[-5]
                }
                json_data.append(json_info)
                count += 1
        print(f'Количество загруженных фотографий на Яндекс.Диск: {count} из {len(file_names)}')
        return json_data

    def upload_photos_from_internet(self, photos, yd_folder_path):
        request_url = self.url + 'resources/upload'
        json_data = []
        count = 0
        for photo in tqdm(photos, desc='Загрузка фотографий на Яндекс.Диск', ncols=100):
            params = {
                'path': f"{yd_folder_path}/{photo['file_name'][:-6]}.jpg",
                'url': photo['url']
            }
            response = requests.post(request_url, headers=self.headers, params=params).json()
            operation_status = self._get_operation_status(response['href'], 2)
            if operation_status == 'success':
                json_info = {
                    'file_name': f"{photo['file_name'][:-6]}.jpg",
                    'size': photo['size']
                }
                json_data.append(json_info)
                count += 1
        print(f'Количество загруженных фотографий на Яндекс.Диск: {count} из {len(photos)}')
        return json_data


class GoogleDrive:
    def __init__(self, token):
        self.headers = {
            'Authorization': f'Bearer {token}'
        }

    def create_folder(self, folder_name, parent_folder_id='root'):
        request_url = 'https://www.googleapis.com/drive/v3/files'
        headers = {'Content-Type': 'application/json'}
        metadata = {
            'name': folder_name,
            'parents': parent_folder_id,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        response = requests.post(request_url, headers={**self.headers, **headers}, data=json.dumps(metadata)).json()
        if 'error' not in response:
            print(f"\nПапка '{folder_name}' успешно создана на Google.Drive")
            time.sleep(0.1)
            return response['id']

    def upload_file_from_pc(self, pc_file_path, file_name, parent_folder_id):
        request_url = 'https://www.googleapis.com/upload/drive/v3/files'
        params = {'uploadType': 'multipart'}
        metadata = {
            'name': file_name,
            'parents': [parent_folder_id]
        }
        with open(pc_file_path, 'rb') as data:
            files = {
                'data': ('metadata', json.dumps(metadata), 'application/json; charset=UTF-8'),
                'file': data
            }
            response = requests.post(request_url, headers=self.headers, params=params, files=files)
            return response.status_code

    def upload_photos_from_pc_folder(self, pc_folder_path, parent_folder_id):
        file_names = os.listdir(pc_folder_path)
        json_data = []
        count = 0
        for file_name in tqdm(file_names, desc='Загрузка фотографий на Google.Drive', ncols=100):
            status_code = self.upload_file_from_pc(
                pc_file_path=f'{pc_folder_path}/{file_name}',
                file_name=f'{file_name[:-6]}.jpg',
                parent_folder_id=parent_folder_id
            )
            if status_code == 200:
                json_info = {
                    'file_name': f'{file_name[:-6]}.jpg',
                    'size': file_name[-5]
                }
                json_data.append(json_info)
                count += 1
        print(f'Количество загруженных фотографий на Google.Drive: {count} из {len(file_names)}')
        return json_data


def select_max_size_photos(photos):
    max_size_photos = []
    size_range = 'smxopqryzw'
    for photo in photos:
        sorted_photo_sizes = sorted(photo['sizes'],
                                    key=lambda size: size_range.index(size['type']))
        max_size_photo = sorted_photo_sizes[-1]
        photo_info = {
            'likes_count': photo['likes']['count'],
            'date': photo['date'],
            'size': max_size_photo['type'],
            'file_name': f"{photo['likes']['count']}_{photo['date']}_{max_size_photo['type']}.jpg",
            'url': max_size_photo['url']
        }
        max_size_photos.append(photo_info)
    return max_size_photos


def create_pc_folder(pc_folder_path):
    if os.path.exists(pc_folder_path):
        for file in os.scandir(pc_folder_path):
            os.remove(file)
    else:
        os.mkdir(pc_folder_path)
        print(f"\nПапка '{pc_folder_path}' успешно создана на ПК")
    return pc_folder_path


def delete_pc_folder(pc_folder_path):
    shutil.rmtree(pc_folder_path)


def download_photos_to_pc_folder(photos, pc_folder_path):
    count = 0
    for photo in tqdm(photos, desc='Загрузка фотографий на ПК', ncols=100):
        response = requests.get(photo['url'])
        if response.status_code == 200:
            with open(f"{pc_folder_path}/{photo['file_name']}", 'wb') as file:
                file.write(response.content)
            count += 1
    print(f'Количество загруженных фотографий на ПК: {count} из {len(photos)}')


def create_json_file(json_data, pc_file_path):
    with open(pc_file_path, 'w', encoding='utf-8') as file:
        json.dump(json_data, file, indent=2)


if __name__ == '__main__':
    vk_id = input('\nID пользователя ВКонтакте: ').strip()
    count = int(input('Количество фотографий для загрузки: '))
    vk_token = input('Токен для доступа к ВКонтакте: ').strip()
    yd_token = input('Токен для доступа к Яндекс.Диску: ').strip()
    gd_token = input('Токен для доступа к Google.Drive: ').strip()

    vk = VKontakte(vk_token)
    photos = vk.get_avatar_photos(vk_id, count)
    # photos = vk.get_all_photos(vk_id)

    max_size_photos = select_max_size_photos(photos)

    pc_folder = create_pc_folder('Photos')
    download_photos_to_pc_folder(max_size_photos, pc_folder)

    yd = YandexDisk(yd_token)
    yd_folder = yd.create_folder('ВКонтакте')
    json_data_yd = yd.upload_photos_from_pc_folder(pc_folder, yd_folder)
    # json_data_yd = yd.upload_photos_from_internet(max_size_photos, yd_folder)
    create_json_file(json_data_yd, 'result_yd.json')

    gd = GoogleDrive(gd_token)
    folder_id = gd.create_folder('ВКонтакте')
    json_data_gd = gd.upload_photos_from_pc_folder(pc_folder, folder_id)
    create_json_file(json_data_gd, 'result_gd.json')

    delete_pc_folder(pc_folder)
