import threading
import time
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from music_manager import MusicFile, DATABASE_URL, MusicManager

app = FastAPI()

# Создаем движок базы данных и сессию
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Инициализируем MusicManager
music_location = "/home/kebab/Музыка/"
music_manager = MusicManager(music_location)


@app.on_event("startup")
def on_startup():
    # Запускаем мониторинг директории в отдельном потоке
    manager_thread = threading.Thread(target=music_manager.start)
    manager_thread.daemon = True
    manager_thread.start()
    # Выполняем первоначальный импорт существующих файлов
    music_manager.start_initial_import()


@app.on_event("shutdown")
def on_shutdown():
    # Останавливаем мониторинг при завершении работы приложения
    music_manager.stop()


@app.get("/tracks/")
def get_all_tracks():
    tracks = session.query(MusicFile).all()
    return [{"id": track.id, "filename": track.filename, "filepath": track.filepath,
             "title": track.title, "artist": track.artist, "album": track.album,
             "genre": track.genre, "length": track.length, "bitrate": track.bitrate} for track in tracks]


@app.get("/tracks/search/")
def search_tracks(title: str = None, artist: str = None):
    if title:
        tracks = session.query(MusicFile).filter(MusicFile.title.ilike(f"%{title}%")).all()
    elif artist:
        tracks = session.query(MusicFile).filter(MusicFile.artist.ilike(f"%{artist}%")).all()
    else:
        raise HTTPException(status_code=400, detail="Specify title or artist for search")

    if not tracks:
        raise HTTPException(status_code=404, detail="No tracks found")

    return [{"id": track.id, "filename": track.filename, "filepath": track.filepath,
             "title": track.title, "artist": track.artist, "album": track.album,
             "genre": track.genre, "length": track.length, "bitrate": track.bitrate} for track in tracks]


@app.get("/tracks/{track_id}/download")
def download_track(track_id: int):
    track = session.query(MusicFile).filter(MusicFile.id == track_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")

    # Возвращаем файл для скачивания
    return FileResponse(path=track.filepath, filename=track.filename, media_type='audio/mpeg')


# Запускаем приложение FastAPI
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
