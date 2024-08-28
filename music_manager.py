import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from mutagen import File as MutagenFile

# Определяем базу данных и модель
DATABASE_URL = "sqlite:///music_library.db"
Base = declarative_base()


class MusicFile(Base):
    __tablename__ = 'music_files'

    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    title = Column(String)
    artist = Column(String)
    album = Column(String)
    genre = Column(String)
    length = Column(Float)
    bitrate = Column(Float)


# Класс для управления музыкальными файлами
class MusicManager(FileSystemEventHandler):
    def __init__(self, music_location):
        self.music_location = music_location
        self.engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

        # Создаем наблюдателя, но не запускаем его
        self.observer = Observer()
        self.observer.schedule(self, self.music_location, recursive=True)

    def process_music_file(self, file_path):
        try:
            audio = MutagenFile(file_path, easy=True)
            if audio is None:
                return None

            title = audio.get('title', [None])[0]
            artist = audio.get('artist', [None])[0]
            album = audio.get('album', [None])[0]
            genre = audio.get('genre', [None])[0]
            length = audio.info.length if audio.info else None
            bitrate = audio.info.bitrate if hasattr(audio.info, 'bitrate') else None

            return {
                "title": title,
                "artist": artist,
                "album": album,
                "genre": genre,
                "length": length,
                "bitrate": bitrate
            }
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
            return None

    def find_music_files(self):
        music_extensions = ['.mp3', '.flac', '.wav', '.m4a', '.aac', '.ogg']
        for root, _, files in os.walk(self.music_location):
            for file in files:
                if any(file.endswith(ext) for ext in music_extensions):
                    yield os.path.join(root, file)

    def add_music_file(self, file_path):
        music_info = self.process_music_file(file_path)
        if music_info:
            existing_file = self.session.query(MusicFile).filter_by(filepath=file_path).first()
            if not existing_file:
                music_file = MusicFile(
                    filename=os.path.basename(file_path),
                    filepath=file_path,
                    title=music_info['title'],
                    artist=music_info['artist'],
                    album=music_info['album'],
                    genre=music_info['genre'],
                    length=music_info['length'],
                    bitrate=music_info['bitrate']
                )
                self.session.add(music_file)
                self.session.commit()

    def on_created(self, event):
        if not event.is_directory:
            self.add_music_file(event.src_path)

    def start(self):
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def start_initial_import(self):
        for file_path in self.find_music_files():
            self.add_music_file(file_path)
