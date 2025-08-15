from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

gauth = GoogleAuth()
gauth.LocalWebserverAuth()  # Откроется браузер для входа в Google

drive = GoogleDrive(gauth)

# prototype for uploading a file
file = drive.CreateFile({'title': 'test.txt'})
file.SetContentString('Hello from osu!downloader')
file.Upload()
print("Файл загружен:", file['title'], "→", file['id'])
